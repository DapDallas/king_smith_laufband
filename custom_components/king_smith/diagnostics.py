"""Diagnostics for the King Smith WalkingPad."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import WalkingPadConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: WalkingPadConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "options": dict(entry.options),
        "connected": coordinator.api.connected,
        "last_update_success": coordinator.last_update_success,
        "update_interval": str(coordinator.update_interval),
        "data": asdict(coordinator.data) if coordinator.data else None,
    }
