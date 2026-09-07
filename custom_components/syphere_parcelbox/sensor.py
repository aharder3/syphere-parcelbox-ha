"""Sensor platform for Syphere Parcelbox."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SyphereRuntimeData
from .entity import SyphereEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Syphere sensors."""
    runtime: SyphereRuntimeData = entry.runtime_data
    async_add_entities(
        [
            SyphereDepositionStateSensor(runtime, entry),
            SyphereDepositionSizeSensor(runtime, entry),
            SyphereAvailableSizeCountSensor(runtime, entry),
        ]
    )


class SyphereDepositionStateSensor(SyphereEntity, SensorEntity):
    """Current deposition workflow state."""

    _attr_translation_key = "deposition_state"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_deposition_state"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("deposition", {}).get("state")


class SyphereDepositionSizeSensor(SyphereEntity, SensorEntity):
    """Size of the active deposition."""

    _attr_translation_key = "deposition_size"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_deposition_size"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("deposition", {}).get("size")


class SyphereAvailableSizeCountSensor(SyphereEntity, SensorEntity):
    """Number of currently available compartment sizes."""

    _attr_translation_key = "available_size_count"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_available_size_count"

    @property
    def native_value(self) -> int:
        return sum(1 for item in self.coordinator.data.get("sizes", []) if item.get("available"))

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        return {
            "sizes": [
                str(item.get("size"))
                for item in self.coordinator.data.get("sizes", [])
                if item.get("available") and item.get("size")
            ]
        }
