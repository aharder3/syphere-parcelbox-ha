"""Binary sensor platform for Syphere Parcelbox."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import slugify

from . import SyphereRuntimeData
from .entity import SyphereEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Syphere binary sensors, including discovered compartment sizes."""
    runtime: SyphereRuntimeData = entry.runtime_data
    coordinator = runtime.coordinator

    async_add_entities(
        [
            SyphereDeliveryPresentBinarySensor(runtime, entry),
            SyphereFixedLockboxBinarySensor(runtime, entry),
            SyphereDepositionEnabledBinarySensor(runtime, entry),
            SyphereBluetoothReachableBinarySensor(runtime, entry),
        ]
    )

    known_sizes: set[str] = set()

    @callback
    def _add_new_size_entities() -> None:
        entities: list[SyphereSizeAvailableBinarySensor] = []
        for item in coordinator.data.get("sizes", []):
            size = item.get("size")
            if not isinstance(size, str) or not size or size in known_sizes:
                continue
            known_sizes.add(size)
            entities.append(SyphereSizeAvailableBinarySensor(runtime, entry, size))
        if entities:
            async_add_entities(entities)

    _add_new_size_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_size_entities))


class SyphereDeliveryPresentBinarySensor(SyphereEntity, BinarySensorEntity):
    """Whether Syphere reports a delivery for the account."""

    _attr_translation_key = "delivery_present"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_delivery_present"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("delivery", {}).get("has_delivery"))


class SyphereFixedLockboxBinarySensor(SyphereEntity, BinarySensorEntity):
    """Whether Syphere reports a fixed lockbox assignment."""

    _attr_translation_key = "fixed_lockbox"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_fixed_lockbox"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("delivery", {}).get("fix_lockbox"))


class SyphereDepositionEnabledBinarySensor(SyphereEntity, BinarySensorEntity):
    """Whether deposition is enabled for the account."""

    _attr_translation_key = "deposition_enabled"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_deposition_enabled"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("deposition_active"))


class SyphereBluetoothReachableBinarySensor(SyphereEntity, BinarySensorEntity):
    """Whether the API reports Bluetooth reachability."""

    _attr_translation_key = "bluetooth_reachable"

    def __init__(self, runtime: SyphereRuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_bluetooth_reachable"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("bt_reachability"))


class SyphereSizeAvailableBinarySensor(SyphereEntity, BinarySensorEntity):
    """Availability of one dynamically discovered compartment size."""

    def __init__(
        self, runtime: SyphereRuntimeData, entry: ConfigEntry, size: str
    ) -> None:
        super().__init__(runtime, entry)
        self.size = size
        self._attr_name = f"Compartment {size} available"
        self._attr_unique_id = f"{entry.entry_id}_size_{slugify(size)}_available"

    @property
    def is_on(self) -> bool:
        for item in self.coordinator.data.get("sizes", []):
            if item.get("size") == self.size:
                return bool(item.get("available"))
        return False
