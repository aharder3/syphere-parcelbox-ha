"""Button platform for Syphere Parcelbox."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SyphereRuntimeData
from .api import SyphereApiError
from .const import NO_DEPOSITION_STATE
from .entity import SyphereEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Syphere action buttons."""
    runtime: SyphereRuntimeData = entry.runtime_data
    async_add_entities(
        [
            SyphereReserveButton(runtime, entry),
            SyphereCancelButton(runtime, entry),
            SyphereOpenDeliveryButton(runtime, entry),
        ]
    )


class _SyphereActionButton(SyphereEntity, ButtonEntity):
    async def _run(self, action) -> None:
        try:
            await action()
        except SyphereApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


class SyphereReserveButton(_SyphereActionButton):
    """Reserve the currently selected size."""

    _attr_translation_key = "reserve_deposition"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_reserve_deposition"

    @property
    def available(self) -> bool:
        if not super().available or not self.coordinator.data.get("deposition_active"):
            return False
        selected = self.runtime.selected_size
        return selected is not None and any(
            item.get("size") == selected and item.get("available")
            for item in self.coordinator.data.get("sizes", [])
        )

    async def async_press(self) -> None:
        size = self.runtime.selected_size
        if size is None:
            raise HomeAssistantError("No Syphere compartment size is selected")
        await self._run(lambda: self.runtime.api.async_reserve_size(size))


class SyphereCancelButton(_SyphereActionButton):
    """Cancel the active deposition."""

    _attr_translation_key = "cancel_deposition"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_cancel_deposition"

    @property
    def available(self) -> bool:
        state = self.coordinator.data.get("deposition", {}).get("state")
        return super().available and bool(state) and state != NO_DEPOSITION_STATE

    async def async_press(self) -> None:
        await self._run(self.runtime.api.async_cancel_deposition)


class SyphereOpenDeliveryButton(_SyphereActionButton):
    """Request opening of the delivery compartment."""

    _attr_translation_key = "open_delivery"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_open_delivery"

    @property
    def available(self) -> bool:
        return super().available and bool(
            self.coordinator.data.get("delivery", {}).get("has_delivery")
        )

    async def async_press(self) -> None:
        await self._run(self.runtime.api.async_open_delivery)
