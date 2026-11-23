"""Sensors for the King Smith WalkingPad."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorExtraStoredData,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfSpeed, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WalkingPadConfigEntry, WalkingPadCoordinator, WalkingPadData
from .entity import WalkingPadEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class WalkingPadSensorDescription(SensorEntityDescription):
    """Describes a WalkingPad sensor."""

    value_fn: Callable[[WalkingPadData], float | int]


SESSION_SENSORS = (
    WalkingPadSensorDescription(
        key="distance",
        translation_key="distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda d: d.distance,
    ),
    WalkingPadSensorDescription(
        key="time",
        translation_key="duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.time,
    ),
    WalkingPadSensorDescription(
        key="speed",
        translation_key="speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.speed,
    ),
    WalkingPadSensorDescription(
        key="steps",
        translation_key="steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.steps,
    ),
    WalkingPadSensorDescription(
        key="step_cadence",
        translation_key="step_cadence",
        native_unit_of_measurement="steps/min",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.step_cadence,
    ),
)

TOTAL_SENSORS = (
    WalkingPadSensorDescription(
        key="total_distance",
        translation_key="total_distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda d: d.distance,
    ),
    WalkingPadSensorDescription(
        key="total_time",
        translation_key="total_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.time,
    ),
    WalkingPadSensorDescription(
        key="total_steps",
        translation_key="total_steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.steps,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WalkingPadConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            *(WalkingPadSensor(coordinator, d) for d in SESSION_SENSORS),
            *(WalkingPadTotalSensor(coordinator, d) for d in TOTAL_SENSORS),
        ]
    )


class WalkingPadSensor(WalkingPadEntity, SensorEntity):
    """Value of the current session."""

    entity_description: WalkingPadSensorDescription

    def __init__(
        self,
        coordinator: WalkingPadCoordinator,
        description: WalkingPadSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        """Current value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


@dataclass
class TotalStoredData(SensorExtraStoredData):
    """Stored total plus the last session value it was based on."""

    last_session_value: float | None = None

    def as_dict(self) -> dict[str, Any]:
        """Serialize."""
        return {**super().as_dict(), "last_session_value": self.last_session_value}


class WalkingPadTotalSensor(WalkingPadSensor, RestoreSensor):
    """Lifetime total, built up from the session values and kept across restarts."""

    def __init__(
        self,
        coordinator: WalkingPadCoordinator,
        description: WalkingPadSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)
        self._total: float = 0
        self._last: float | None = None

    async def async_added_to_hass(self) -> None:
        """Restore total and last seen session value."""
        await super().async_added_to_hass()
        if (extra := await self.async_get_last_extra_data()) is None:
            return
        data = extra.as_dict()
        if (stored := SensorExtraStoredData.from_dict(data)) is not None:
            try:
                self._total = float(stored.native_value or 0)
            except (TypeError, ValueError):
                self._total = 0
        self._last = data.get("last_session_value")
        if self.coordinator.data is not None:
            self._accumulate(self.entity_description.value_fn(self.coordinator.data))

    @property
    def extra_restore_state_data(self) -> TotalStoredData:
        """Data to keep across restarts."""
        return TotalStoredData(
            self.native_value, self.native_unit_of_measurement, self._last
        )

    def _accumulate(self, value: float) -> None:
        if self._last is None:
            # Unknown baseline: don't count what may already be counted.
            pass
        elif value >= self._last:
            self._total += value - self._last
        else:
            # Session was reset on the pad, a new one started.
            self._total += value
        self._last = value

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is not None:
            self._accumulate(self.entity_description.value_fn(self.coordinator.data))
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float | int:
        """Total value."""
        if self.entity_description.key == "total_distance":
            return round(self._total, 2)
        return int(self._total)
