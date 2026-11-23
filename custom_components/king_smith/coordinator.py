"""Coordinator for the King Smith WalkingPad."""

from __future__ import annotations

from collections.abc import Coroutine
from dataclasses import dataclass, replace
from datetime import timedelta
import logging
import time
from typing import Any

from bleak.backends.device import BLEDevice

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, CONF_MAC, CONF_TYPE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_SESSION_DONE,
    EVENT_SESSION_START,
    SESSION_DONE,
    SESSION_START,
)
from .walking_pad import (
    MODE_MANUAL,
    MODE_STANDBY,
    WalkingPadApi,
    WalkingPadError,
    WalkingPadStatus,
)

_LOGGER = logging.getLogger(__name__)

# Right after a command the pad keeps reporting the old values for a while.
# Commanded values are shown until the pad confirms them or the hold expires.
OPTIMISTIC_HOLD = 5.0  # seconds
# After "start" the pad counts down a few seconds before the belt moves.
START_HOLD = 10.0  # seconds
# Poll this often while the belt runs, so speed and distance update live.
ACTIVE_SCAN_INTERVAL = timedelta(seconds=1)

type WalkingPadConfigEntry = ConfigEntry[WalkingPadCoordinator]


@dataclass(frozen=True, slots=True)
class WalkingPadData:
    """State of the pad as exposed to the entities."""

    speed: float
    mode: int
    belt_state: int
    time: int
    distance: float
    steps: int
    step_cadence: float
    moving: bool


class WalkingPadCoordinator(DataUpdateCoordinator[WalkingPadData]):
    """Polls the pad and turns its status into entity state and events."""

    config_entry: WalkingPadConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: WalkingPadConfigEntry, ble_device: BLEDevice
    ) -> None:
        """Initialize the coordinator."""
        self._idle_interval = timedelta(
            seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=self._idle_interval,
        )
        self.mac: str = entry.data[CONF_MAC].upper()
        self.api = WalkingPadApi(ble_device, self._handle_push, self._handle_disconnect)
        self._held: dict[str, Any] = {}
        self._hold_until = 0.0
        self._previous: WalkingPadStatus | None = None

    async def _async_update_data(self) -> WalkingPadData:
        if not self.api.connected:
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )
            if ble_device is None:
                raise UpdateFailed(
                    "WalkingPad is not in Bluetooth range or switched off"
                )
            self.api.set_ble_device(ble_device)
        try:
            await self.api.connect()
            status = await self.api.request_status()
        except WalkingPadError as err:
            await self.api.disconnect()
            raise UpdateFailed(str(err)) from err
        return self._process(status)

    async def async_shutdown(self) -> None:
        """Disconnect when the entry is unloaded."""
        await super().async_shutdown()
        await self.api.disconnect()

    @callback
    def _handle_push(self, status: WalkingPadStatus) -> None:
        """Status arrived without being asked for."""
        self.async_set_updated_data(self._process(status))

    @callback
    def _handle_disconnect(self) -> None:
        self.async_update_listeners()

    def _process(self, status: WalkingPadStatus) -> WalkingPadData:
        previous = self._previous
        self._previous = status

        cadence = 0.0
        if (
            previous is not None
            and status.speed > 0
            and status.time > previous.time
            and status.steps >= previous.steps
        ):
            cadence = round(
                (status.steps - previous.steps) * 60 / (status.time - previous.time), 1
            )

        if previous is not None:
            self._fire_session_events(previous, status)

        data = WalkingPadData(
            speed=status.speed,
            mode=status.mode,
            belt_state=status.belt_state,
            time=status.time,
            distance=status.distance,
            steps=status.steps,
            step_cadence=cadence,
            moving=status.speed > 0,
        )
        data = self._apply_held(data)
        self._set_interval(data)
        return data

    def _apply_held(self, data: WalkingPadData) -> WalkingPadData:
        """Keep showing commanded values until the pad confirms them."""
        if time.monotonic() >= self._hold_until:
            self._held.clear()
        self._held = {k: v for k, v in self._held.items() if getattr(data, k) != v}
        return replace(data, **self._held) if self._held else data

    def _set_interval(self, data: WalkingPadData) -> None:
        """Poll fast while the belt runs or a command is pending."""
        active = data.moving or bool(self._held)
        self.update_interval = ACTIVE_SCAN_INTERVAL if active else self._idle_interval

    def _fire_session_events(
        self, previous: WalkingPadStatus, status: WalkingPadStatus
    ) -> None:
        device = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, self.mac)}
        )
        base = {ATTR_DEVICE_ID: device.id if device else None}
        now = dt_util.utcnow()

        if previous.time > 0 and status.time < previous.time:
            minutes = previous.time / 60
            self.hass.bus.async_fire(
                EVENT_SESSION_DONE,
                {
                    **base,
                    CONF_TYPE: SESSION_DONE,
                    "start_time": (now - timedelta(seconds=previous.time)).isoformat(),
                    "end_time": now.isoformat(),
                    "duration": previous.time,
                    "steps": previous.steps,
                    "dist": previous.distance,
                    "avg_step_cadence": round(previous.steps / minutes, 1),
                    "avg_speed": round(previous.distance / (minutes / 60), 2),
                },
            )
        elif previous.time == 0 and status.time > 0:
            self.hass.bus.async_fire(
                EVENT_SESSION_START,
                {**base, CONF_TYPE: SESSION_START, "start_time": now.isoformat()},
            )

    async def _command(
        self,
        coro: Coroutine[Any, Any, None],
        hold: float = OPTIMISTIC_HOLD,
        **optimistic: Any,
    ) -> None:
        try:
            await coro
        except WalkingPadError as err:
            raise HomeAssistantError(f"WalkingPad command failed: {err}") from err
        if self.data is None:
            return
        self._held = optimistic
        self._hold_until = time.monotonic() + hold
        data = replace(self.data, **optimistic)
        self._set_interval(data)
        self.async_set_updated_data(data)

    async def async_start(self) -> None:
        """Start the belt."""
        await self._command(
            self.api.start(), hold=START_HOLD, mode=MODE_MANUAL, moving=True
        )

    async def async_stop(self) -> None:
        """Stop the belt."""
        await self._command(self.api.stop(), speed=0.0, mode=MODE_STANDBY, moving=False)

    async def async_set_speed(self, speed: float) -> None:
        """Change the belt speed."""
        await self._command(self.api.set_speed(speed), speed=speed)
