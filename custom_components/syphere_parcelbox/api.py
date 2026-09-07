"""Async client for the undocumented Syphere Parcelbox cloud API.

The client intentionally never logs request/response bodies. API responses may
contain PINs and personal data, so public helpers return only the fields needed
by Home Assistant.
"""

from __future__ import annotations

import base64
from collections.abc import Awaitable, Callable
import hashlib
import inspect
import json
from typing import Any

import aiohttp

DEFAULT_OAUTH_CLIENT_ID = "iCLRmUf6C1ZbrlPDTWQ1"

TokenUpdateCallback = Callable[[dict[str, str]], Awaitable[None] | None]


class SyphereApiError(Exception):
    """Base error for Syphere API failures."""


class SyphereAuthError(SyphereApiError):
    """Authentication or token refresh failed."""


class SyphereClientIdError(SyphereAuthError):
    """The OAuth client ID could not be determined."""


class SyphereConnectionError(SyphereApiError):
    """The Syphere API could not be reached."""


class SyphereUnavailableSizeError(SyphereApiError):
    """The requested compartment size is not currently available."""


class SyphereNoDepositionError(SyphereApiError):
    """There is no active deposition to cancel."""


def _decode_jwt_claims_unverified(token: str) -> dict[str, Any]:
    """Decode JWT payload claims without verifying the signature.

    This is used only to read the server-issued ``client_id`` claim from an
    access token that has already been accepted by Syphere. It is not used for
    authentication or authorization decisions.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        data = json.loads(decoded.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


async def _read_json_response(response: aiohttp.ClientResponse, *, context: str) -> Any:
    """Read a JSON response without leaking its body in errors."""
    if response.status == 204 or response.content_length == 0:
        return None

    text = await response.text()
    if not text.strip():
        return None
    try:
        return await response.json(content_type=None)
    except (ValueError, aiohttp.ContentTypeError) as err:
        raise SyphereApiError(
            f"Syphere returned an invalid JSON response for {context}"
        ) from err


class SyphereApiClient:
    """Minimal async client for the observed Syphere Parcelbox API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        base_url: str,
        access_token: str,
        refresh_token: str,
        client_id: str,
        token_update_callback: TokenUpdateCallback | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._token_update_callback = token_update_callback

    @property
    def access_token(self) -> str:
        """Return the current access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str:
        """Return the current refresh token."""
        return self._refresh_token

    @property
    def client_id(self) -> str:
        """Return the current OAuth client ID."""
        return self._client_id

    @classmethod
    async def async_login(
        cls,
        session: aiohttp.ClientSession,
        *,
        base_url: str,
        email: str,
        password: str,
        client_id: str | None = None,
    ) -> "SyphereApiClient":
        """Authenticate exactly like the observed official iOS app.

        The Syphere app sends a compact JSON document as the raw HTTP body,
        while declaring ``application/x-www-form-urlencoded`` as the content
        type. This is unusual but intentionally reproduced here because the
        backend expects the app's wire format.

        The OAuth client ID is a public application identifier, not a secret.
        The observed official-app value is used by default and can still be
        overridden by callers for another Syphere deployment.
        """
        clean_base_url = base_url.rstrip("/")
        resolved_client_id = (client_id or DEFAULT_OAUTH_CLIENT_ID).strip()
        if not resolved_client_id:
            raise SyphereClientIdError("Syphere OAuth client ID is missing")

        payload = {
            "username": email.strip(),
            "password": password,
            "grant_type": "password",
            "client_id": resolved_client_id,
        }
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with session.request(
                "POST",
                f"{clean_base_url}/api/oauth/token",
                headers=headers,
                data=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status in (400, 401, 403):
                    raise SyphereAuthError(
                        f"Syphere login failed (HTTP {response.status})"
                    )
                if response.status >= 400:
                    raise SyphereApiError(
                        f"Syphere API returned HTTP {response.status} for login"
                    )
                data = await _read_json_response(response, context="login")
        except SyphereApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SyphereConnectionError("Unable to connect to the Syphere API") from err

        if not isinstance(data, dict):
            raise SyphereAuthError("Syphere login returned no token data")

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if not isinstance(access_token, str) or not access_token:
            raise SyphereAuthError("Syphere login returned no access token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise SyphereAuthError("Syphere login returned no refresh token")

        # Prefer a server-provided/issued client_id if available, while keeping
        # the app identifier used for the login as a reliable fallback.
        response_client_id = data.get("client_id")
        if isinstance(response_client_id, str) and response_client_id:
            resolved_client_id = response_client_id
        else:
            claims = _decode_jwt_claims_unverified(access_token)
            claim_client_id = claims.get("client_id")
            if isinstance(claim_client_id, str) and claim_client_id:
                resolved_client_id = claim_client_id

        return cls(
            session,
            base_url=clean_base_url,
            access_token=access_token,
            refresh_token=refresh_token,
            client_id=resolved_client_id,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> Any:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token}",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401 and retry_auth:
                    await self.async_refresh_token()
                    return await self._request(
                        method, path, payload=payload, retry_auth=False
                    )

                if response.status in (401, 403):
                    raise SyphereAuthError(
                        f"Syphere authentication failed (HTTP {response.status})"
                    )
                if response.status >= 400:
                    raise SyphereApiError(
                        f"Syphere API returned HTTP {response.status} for {path}"
                    )

                return await _read_json_response(response, context=path)
        except SyphereApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SyphereConnectionError("Unable to connect to the Syphere API") from err

    async def async_refresh_token(self) -> None:
        """Refresh OAuth tokens using the flow observed in the official app."""
        payload = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
            "client_id": self._client_id,
        }

        data = await self._request(
            "POST", "/api/oauth/token", payload=payload, retry_auth=False
        )
        if not isinstance(data, dict):
            raise SyphereAuthError("Syphere token refresh returned no token data")

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if not isinstance(access_token, str) or not access_token:
            raise SyphereAuthError("Syphere token refresh returned no access token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise SyphereAuthError("Syphere token refresh returned no refresh token")

        self._access_token = access_token
        self._refresh_token = refresh_token

        if self._token_update_callback is not None:
            result = self._token_update_callback(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            )
            if inspect.isawaitable(result):
                await result

    async def _async_get_homepage_raw(self) -> dict[str, Any]:
        data = await self._request("GET", "/api/user/homepage")
        if not isinstance(data, dict):
            raise SyphereApiError("Syphere homepage returned an invalid response")
        return data

    async def async_get_device_fingerprint(self) -> str | None:
        """Return a one-way fingerprint for duplicate-entry detection.

        The raw Bluetooth identifier is never returned to Home Assistant.
        """
        data = await self._async_get_homepage_raw()
        bt_ident = data.get("bt_ident")
        if not isinstance(bt_ident, str) or not bt_ident:
            return None
        return hashlib.sha256(bt_ident.encode("utf-8")).hexdigest()[:24]

    async def async_get_status(self) -> dict[str, Any]:
        """Return a privacy-minimized account/parcelbox status."""
        data = await self._async_get_homepage_raw()
        delivery = data.get("delivery") if isinstance(data.get("delivery"), dict) else {}
        deposition = (
            data.get("deposition") if isinstance(data.get("deposition"), dict) else {}
        )

        return {
            "delivery": {
                "has_delivery": bool(delivery.get("has_delivery", False)),
                "fix_lockbox": bool(delivery.get("fix_lockbox", False)),
            },
            "deposition": {
                "state": deposition.get("state"),
                "size": deposition.get("size"),
            },
            "deposition_active": bool(data.get("deposition_active", False)),
            "bt_reachability": bool(data.get("bt_reachability", False)),
        }

    async def _async_get_sizes_raw(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/deposition/size")
        if not isinstance(data, list):
            raise SyphereApiError("Syphere size endpoint returned an invalid response")
        return [item for item in data if isinstance(item, dict)]

    async def async_get_sizes(self) -> list[dict[str, Any]]:
        """Return compartment availability without backend lockbox IDs."""
        data = await self._async_get_sizes_raw()
        result: list[dict[str, Any]] = []
        for item in data:
            size = item.get("size")
            if not isinstance(size, str) or not size:
                continue
            result.append(
                {
                    "size": size,
                    "available": bool(item.get("available", False)),
                    "state": item.get("state"),
                }
            )
        return result

    async def async_reserve_size(self, size: str) -> dict[str, Any]:
        """Reserve a currently available compartment of the requested size."""
        requested = size.casefold()
        for item in await self._async_get_sizes_raw():
            api_size = item.get("size")
            if (
                isinstance(api_size, str)
                and api_size.casefold() == requested
                and item.get("available") is True
                and isinstance(item.get("id"), int)
            ):
                data = await self._request(
                    "POST",
                    "/api/deposition/reservation",
                    payload={"lockbox_id": item["id"]},
                )
                return data if isinstance(data, dict) else {}

        raise SyphereUnavailableSizeError(
            f"No available Syphere compartment for size {size!r}"
        )

    async def async_cancel_deposition(self) -> None:
        """Cancel the currently active deposition."""
        data = await self._async_get_homepage_raw()
        deposition = data.get("deposition")
        deposition_id = (
            deposition.get("deposition_id") if isinstance(deposition, dict) else None
        )
        if not isinstance(deposition_id, int):
            raise SyphereNoDepositionError("There is no active Syphere deposition")

        await self._request(
            "POST",
            "/api/deposition/cancel",
            payload={"deposition_id": deposition_id},
        )

    async def async_open_delivery(self) -> None:
        """Request opening of the compartment holding the current delivery."""
        await self._request("POST", "/api/delivery/open", payload={})
