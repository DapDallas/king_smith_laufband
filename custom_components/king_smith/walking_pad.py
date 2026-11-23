"""Bluetooth client for King Smith WalkingPad treadmills.

The protocol is taken from ph4-walkingpad (https://github.com/ph4r05/ph4-walkingpad).
Commands are written to characteristic FE02, the pad answers on FE01 via
notifications. The pad only sends its status when asked for it, so it has to
be polled.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import logging
import time

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)

_LOGGER = logging.getLogger(__name__)

CHAR_NOTIFY = "0000fe01-0000-1000-8000-00805f9b34fb"
CHAR_WRITE = "0000fe02-0000-1000-8000-00805f9b34fb"

MODE_AUTO = 0
MODE_MANUAL = 1
MODE_STANDBY = 2

# The pad drops commands that arrive too quickly after each other.
MIN_COMMAND_SPACING = 0.7  # seconds
STATUS_TIMEOUT = 5.0  # seconds


class WalkingPadError(Exception):
    """Communication with the WalkingPad failed."""


@dataclass(frozen=True, slots=True)
class WalkingPadStatus:
    """Status message (type F8 A2) reported by the pad."""

    belt_state: int
    speed: float  # km/h
    mode: int
    time: int  # seconds in the current session
    distance: float  # km in the current session
    steps: int

    @classmethod
    def from_bytes(cls, data: bytes | bytearray) -> WalkingPadStatus | None:
        """Parse a notification, returns None for other message types."""
        if len(data) < 17 or data[0] != 0xF8 or data[1] != 0xA2:
            return None
        return cls(
            belt_state=data[2],
            speed=data[3] / 10,
            mode=data[4],
            time=int.from_bytes(data[5:8], "big"),
            distance=int.from_bytes(data[8:11], "big") / 100,
            steps=int.from_bytes(data[11:14], "big"),
        )


def _command(*payload: int) -> bytes:
    """Build a command frame: F7 <payload> <checksum> FD."""
    return bytes([0xF7, *payload, sum(payload) % 256, 0xFD])


class WalkingPadApi:
    """Connection to a single WalkingPad."""

    def __init__(
        self,
        ble_device: BLEDevice,
        status_callback: Callable[[WalkingPadStatus], None],
        disconnect_callback: Callable[[], None],
    ) -> None:
        """Initialize the client."""
        self._ble_device = ble_device
        self._status_callback = status_callback
        self._disconnect_callback = disconnect_callback
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self._last_command = 0.0
        self._status_waiter: asyncio.Future[WalkingPadStatus] | None = None

    @property
    def address(self) -> str:
        """Bluetooth address of the pad."""
        return self._ble_device.address

    @property
    def connected(self) -> bool:
        """Whether a connection is established."""
        return self._client is not None and self._client.is_connected

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        """Update the BLE device, e.g. when another adapter or proxy sees it."""
        self._ble_device = ble_device

    async def connect(self) -> None:
        """Connect and subscribe to status notifications."""
        async with self._lock:
            if self.connected:
                return
            _LOGGER.debug("Connecting to %s", self.address)
            try:
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    self._ble_device,
                    self._ble_device.name or self.address,
                    disconnected_callback=self._on_disconnect,
                    ble_device_callback=lambda: self._ble_device,
                )
                await client.start_notify(CHAR_NOTIFY, self._on_notify)
            except (BleakError, TimeoutError) as err:
                raise WalkingPadError(f"Could not connect: {err}") from err
            self._client = client
            _LOGGER.debug("Connected to %s", self.address)

    async def disconnect(self) -> None:
        """Close the connection."""
        async with self._lock:
            client, self._client = self._client, None
            if client is not None:
                await client.disconnect()

    def _on_disconnect(self, client: BleakClientWithServiceCache) -> None:
        if client is not self._client:
            return
        _LOGGER.debug("Disconnected from %s", self.address)
        self._client = None
        if self._status_waiter is not None and not self._status_waiter.done():
            self._status_waiter.set_exception(WalkingPadError("Disconnected"))
        self._disconnect_callback()

    def _on_notify(self, _sender: object, data: bytearray) -> None:
        status = WalkingPadStatus.from_bytes(data)
        if status is None:
            _LOGGER.debug("Ignoring message %s", data.hex())
            return
        if self._status_waiter is not None and not self._status_waiter.done():
            self._status_waiter.set_result(status)
        else:
            self._status_callback(status)

    async def _send(self, command: bytes) -> None:
        """Send a command, caller must hold the lock."""
        if self._client is None or not self._client.is_connected:
            raise WalkingPadError("Not connected")
        wait = MIN_COMMAND_SPACING - (time.monotonic() - self._last_command)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            await self._client.write_gatt_char(CHAR_WRITE, command)
        except BleakError as err:
            raise WalkingPadError(f"Could not send command: {err}") from err
        finally:
            self._last_command = time.monotonic()

    async def _run(self, *commands: bytes) -> None:
        async with self._lock:
            for command in commands:
                await self._send(command)

    async def request_status(self) -> WalkingPadStatus:
        """Ask the pad for its status and wait for the answer."""
        async with self._lock:
            self._status_waiter = asyncio.get_running_loop().create_future()
            try:
                await self._send(_command(0xA2, 0x00, 0x00))
                async with asyncio.timeout(STATUS_TIMEOUT):
                    return await self._status_waiter
            except TimeoutError as err:
                raise WalkingPadError("No status received") from err
            finally:
                self._status_waiter = None

    async def set_mode(self, mode: int) -> None:
        """Switch between auto, manual and standby mode."""
        await self._run(_command(0xA2, 0x02, mode))

    async def set_speed(self, speed: float) -> None:
        """Set the belt speed in km/h (0 stops the belt)."""
        await self._run(_command(0xA2, 0x01, round(speed * 10)))

    async def start(self) -> None:
        """Switch to manual mode and start the belt."""
        await self._run(_command(0xA2, 0x02, MODE_MANUAL), _command(0xA2, 0x04, 0x01))

    async def stop(self) -> None:
        """Stop the belt and put the pad into standby."""
        await self._run(_command(0xA2, 0x01, 0x00), _command(0xA2, 0x02, MODE_STANDBY))
