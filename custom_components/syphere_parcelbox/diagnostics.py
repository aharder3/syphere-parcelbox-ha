"""Diagnostics for Syphere Parcelbox."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import SyphereRuntimeData
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_EMAIL,
    CONF_REFRESH_TOKEN,
)

TO_REDACT = {CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN, CONF_CLIENT_ID, CONF_EMAIL}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return privacy-minimized diagnostics."""
    runtime: SyphereRuntimeData = entry.runtime_data
    return {
        "config": async_redact_data(dict(entry.data), TO_REDACT),
        "data": runtime.coordinator.data,
        "selected_size": runtime.selected_size,
    }
