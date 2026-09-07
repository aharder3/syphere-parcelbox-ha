"""Select platform for Syphere Parcelbox."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
    """Set up deposition-size selection."""
    runtime: SyphereRuntimeData = entry.runtime_data
    async_add_entities([SyphereDepositionSizeSelect(runtime, entry)])


class SyphereDepositionSizeSelect(SyphereEntity, SelectEntity):
    """Locally select the size to reserve with the reserve button."""

    _attr_translation_key = "deposition_size_select"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_deposition_size_select"
        self._sync_selection()

    @property
    def options(self) -> list[str]:
        return [
            str(item["size"])
            for item in self.coordinator.data.get("sizes", [])
            if item.get("available") and item.get("size")
        ]

    @property
    def current_option(self) -> str | None:
        return self.runtime.selected_size

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ValueError(f"Unsupported or unavailable compartment size: {option}")
        self.runtime.selected_size = option
        self.async_write_ha_state()

    def _sync_selection(self) -> None:
        options = self.options
        if self.runtime.selected_size not in options:
            self.runtime.selected_size = options[0] if options else None

    def _handle_coordinator_update(self) -> None:
        self._sync_selection()
        super()._handle_coordinator_update()
