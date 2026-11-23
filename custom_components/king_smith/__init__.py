"""The King Smith WalkingPad integration."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.const import CONF_MAC, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import WalkingPadConfigEntry, WalkingPadCoordinator

PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: WalkingPadConfigEntry) -> bool:
    """Set up a WalkingPad from a config entry."""
    mac = entry.data[CONF_MAC].upper()
    ble_device = bluetooth.async_ble_device_from_address(hass, mac, connectable=True)
    if ble_device is None:
        if bluetooth.async_scanner_count(hass, connectable=True) < 1:
            raise ConfigEntryNotReady(
                "No Bluetooth adapter or proxy found. Enable the Bluetooth "
                "integration or set up an ESPHome Bluetooth proxy."
            )
        raise ConfigEntryNotReady(f"WalkingPad {mac} not found, is it switched on?")

    coordinator = WalkingPadCoordinator(hass, entry, ble_device)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    @callback
    def _advertisement(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        _change: bluetooth.BluetoothChange,
    ) -> None:
        coordinator.api.set_ble_device(service_info.device)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _advertisement,
            bluetooth.BluetoothCallbackMatcher(address=mac, connectable=True),
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: WalkingPadConfigEntry
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: WalkingPadConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
        bluetooth.async_rediscover_address(hass, entry.data[CONF_MAC].upper())
    return unload_ok
