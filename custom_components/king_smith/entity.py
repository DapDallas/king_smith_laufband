"""Base entity for the King Smith WalkingPad."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import WalkingPadCoordinator


class WalkingPadEntity(CoordinatorEntity[WalkingPadCoordinator]):
    """Entity belonging to a WalkingPad device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WalkingPadCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        mac = coordinator.mac
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={(CONNECTION_BLUETOOTH, mac)},
            name=coordinator.config_entry.title,
            manufacturer=MANUFACTURER,
        )

    @property
    def available(self) -> bool:
        """Available while connected and a status has been received."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.api.connected
        )
