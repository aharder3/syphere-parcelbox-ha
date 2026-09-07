"""Constants for the Syphere Parcelbox integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "syphere_parcelbox"
NAME = "Syphere Parcelbox"
VERSION = "0.2.1"

DEFAULT_BASE_URL = "https://pbb.syphere.net:9997"
DEFAULT_SCAN_INTERVAL = 60

CONF_EMAIL = "email"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_CLIENT_ID = "client_id"
CONF_BASE_URL = "base_url"

NO_DEPOSITION_STATE = "no_deposition"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SENSOR,
]
