"""Speed control for the King Smith WalkingPad."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WalkingPadConfigEntry
from .entity import WalkingPadEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WalkingPadConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the speed entity."""
    async_add_entities([WalkingPadSpeed(entry.runtime_data, "speed")])


class WalkingPadSpeed(WalkingPadEntity, NumberEntity):
    """Target belt speed."""

    _attr_translation_key = "speed"
    _attr_device_class = NumberDeviceClass.SPEED
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_min_value = 0.0
    _attr_native_max_value = 6.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float | None:
        """Current speed."""
        return self.coordinator.data.speed if self.coordinator.data else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the speed."""
        await self.coordinator.async_set_speed(value)
