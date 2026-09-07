"""Data coordinator for Syphere Parcelbox."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SyphereApiClient, SyphereApiError, SyphereAuthError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN


class SyphereCoordinator(DataUpdateCoordinator[dict]):
    """Coordinate cloud polling for all Syphere entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: SyphereApiClient,
    ) -> None:
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            status = await self.api.async_get_status()
            sizes = (
                await self.api.async_get_sizes()
                if status.get("deposition_active")
                else []
            )
            return {**status, "sizes": sizes}
        except SyphereAuthError as err:
            raise ConfigEntryAuthFailed from err
        except SyphereApiError as err:
            raise UpdateFailed(str(err)) from err
