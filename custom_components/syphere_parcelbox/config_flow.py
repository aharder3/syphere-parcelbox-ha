"""Config flow for Syphere Parcelbox."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    SyphereApiClient,
    SyphereApiError,
    SyphereAuthError,
    SyphereClientIdError,
    SyphereConnectionError,
)
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_BASE_URL,
    CONF_CLIENT_ID,
    CONF_EMAIL,
    CONF_REFRESH_TOKEN,
    DEFAULT_BASE_URL,
    DOMAIN,
    NAME,
)


def _login_schema(defaults: dict[str, str] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_EMAIL,
                default=defaults.get(CONF_EMAIL, ""),
            ): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(
                CONF_CLIENT_ID,
                default=defaults.get(CONF_CLIENT_ID, ""),
            ): str,
            vol.Optional(
                CONF_BASE_URL,
                default=defaults.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            ): str,
        }
    )


class SyphereConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Syphere Parcelbox."""

    VERSION = 1

    async def _login_and_validate(
        self, user_input: dict[str, Any]
    ) -> tuple[dict[str, str], str | None]:
        base_url = str(user_input[CONF_BASE_URL]).strip().rstrip("/")
        email = str(user_input[CONF_EMAIL]).strip()
        password = str(user_input[CONF_PASSWORD])
        optional_client_id = str(user_input.get(CONF_CLIENT_ID, "")).strip()

        client = await SyphereApiClient.async_login(
            async_get_clientsession(self.hass),
            base_url=base_url,
            email=email,
            password=password,
            client_id=optional_client_id or None,
        )

        # Validate the newly issued token against a normal authenticated API
        # call and derive a stable, one-way device fingerprint for duplicates.
        fingerprint = await client.async_get_device_fingerprint()
        data = {
            CONF_EMAIL: email,
            CONF_BASE_URL: base_url,
            CONF_ACCESS_TOKEN: client.access_token,
            CONF_REFRESH_TOKEN: client.refresh_token,
            CONF_CLIENT_ID: client.client_id,
        }
        return data, fingerprint

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle initial setup with Syphere email/password login."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                data, fingerprint = await self._login_and_validate(user_input)
            except SyphereClientIdError:
                errors["base"] = "client_id_required"
            except SyphereAuthError:
                errors["base"] = "invalid_auth"
            except SyphereConnectionError:
                errors["base"] = "cannot_connect"
            except SyphereApiError:
                errors["base"] = "unknown"
            else:
                if fingerprint:
                    await self.async_set_unique_id(fingerprint)
                    self._abort_if_unique_id_configured()
                return self.async_create_entry(title=NAME, data=data)

        defaults = {
            key: str(value)
            for key, value in (user_input or {}).items()
            if key != CONF_PASSWORD
        }
        return self.async_show_form(
            step_id="user",
            data_schema=_login_schema(defaults),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        """Start reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        """Reauthenticate with email/password; passwords are never persisted."""
        errors: dict[str, str] = {}
        defaults = {
            CONF_EMAIL: str(self._reauth_entry.data.get(CONF_EMAIL, "")),
            CONF_CLIENT_ID: str(self._reauth_entry.data.get(CONF_CLIENT_ID, "")),
            CONF_BASE_URL: str(
                self._reauth_entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
            ),
        }

        if user_input is not None:
            try:
                data, _ = await self._login_and_validate(user_input)
            except SyphereClientIdError:
                errors["base"] = "client_id_required"
            except SyphereAuthError:
                errors["base"] = "invalid_auth"
            except SyphereConnectionError:
                errors["base"] = "cannot_connect"
            except SyphereApiError:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates=data,
                )

            defaults.update(
                {
                    key: str(value)
                    for key, value in user_input.items()
                    if key != CONF_PASSWORD
                }
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_login_schema(defaults),
            errors=errors,
        )
