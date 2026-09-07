"""Base entity classes for Syphere Parcelbox."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SyphereRuntimeData
from .const import DOMAIN
from .coordinator import SyphereCoordinator


class SyphereEntity(CoordinatorEntity[SyphereCoordinator]):
    """Base entity for the Syphere Parcelbox service."""

    _attr_has_entity_name = True

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime.coordinator)
        self.runtime = runtime
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Syphere Parcelbox",
            manufacturer="Synomics",
            model="Syphere Parcelbox",
        )
