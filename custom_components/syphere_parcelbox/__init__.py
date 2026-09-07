"""Syphere Parcelbox integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SyphereApiClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_BASE_URL,
    CONF_CLIENT_ID,
    CONF_REFRESH_TOKEN,
    PLATFORMS,
)
from .coordinator import SyphereCoordinator


@dataclass
class SyphereRuntimeData:
    """Runtime objects shared by Syphere platforms."""

    api: SyphereApiClient
    coordinator: SyphereCoordinator
    selected_size: str | None = None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Syphere Parcelbox from a config entry."""

    async def _tokens_updated(tokens: dict[str, str]) -> None:
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_ACCESS_TOKEN: tokens[CONF_ACCESS_TOKEN],
                CONF_REFRESH_TOKEN: tokens[CONF_REFRESH_TOKEN],
            },
        )

    api = SyphereApiClient(
        async_get_clientsession(hass),
        base_url=entry.data[CONF_BASE_URL],
        access_token=entry.data[CONF_ACCESS_TOKEN],
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
        client_id=entry.data[CONF_CLIENT_ID],
        token_update_callback=_tokens_updated,
    )
    coordinator = SyphereCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = SyphereRuntimeData(api=api, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Syphere config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
