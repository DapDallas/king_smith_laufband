"""Belt switch for the King Smith WalkingPad."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up the belt switch."""
    async_add_entities([WalkingPadSwitch(entry.runtime_data, "switch")])


class WalkingPadSwitch(WalkingPadEntity, SwitchEntity):
    """Starts and stops the belt."""

    _attr_name = None
    _attr_icon = "mdi:treadmill"

    @property
    def is_on(self) -> bool | None:
        """Whether the belt is running."""
        return self.coordinator.data.moving if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the belt."""
        await self.coordinator.async_start()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the belt."""
        await self.coordinator.async_stop()
