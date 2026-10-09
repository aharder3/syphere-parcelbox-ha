"""Tests for the standalone Syphere API client."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

API_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "syphere_parcelbox"
    / "api.py"
)
spec = importlib.util.spec_from_file_location("syphere_api", API_PATH)
api_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(api_module)
SyphereApiClient = api_module.SyphereApiClient
SyphereAuthError = api_module.SyphereAuthError
DEFAULT_OAUTH_CLIENT_ID = api_module.DEFAULT_OAUTH_CLIENT_ID


class FakeResponse:
    def __init__(self, status: int, data: Any = None) -> None:
        self.status = status
        self.data = data
        self.content_length = 0 if data is None else 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self) -> str:
        if self.data is None:
            return ""
        return json.dumps(self.data)

    async def json(self, content_type=None):
        return self.data


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


def make_client(session, callback=None):
    return SyphereApiClient(
        session,
        base_url="https://example.invalid:9997",
        access_token="access-placeholder",
        refresh_token="refresh-placeholder",
        client_id="client-placeholder",
        token_update_callback=callback,
    )


def fake_jwt(claims: dict[str, Any]) -> str:
    def enc(data: dict[str, Any]) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{enc({'alg': 'none', 'typ': 'JWT'})}.{enc(claims)}.signature-placeholder"


@pytest.mark.asyncio
async def test_login_matches_observed_official_app_wire_format():
    access = fake_jwt({"client_id": DEFAULT_OAUTH_CLIENT_ID})
    session = FakeSession(
        [FakeResponse(200, {"access_token": access, "refresh_token": "new-refresh"})]
    )

    client = await SyphereApiClient.async_login(
        session,
        base_url="https://example.invalid:9997",
        email="person@example.invalid",
        password="secret-placeholder",
    )

    call = session.calls[0]
    assert call["method"] == "POST"
    assert call["url"].endswith("/api/oauth/token")
    assert "Authorization" not in call["headers"]
    assert call["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert "json" not in call
    assert json.loads(call["data"]) == {
        "username": "person@example.invalid",
        "password": "secret-placeholder",
        "grant_type": "password",
        "client_id": DEFAULT_OAUTH_CLIENT_ID,
    }
    # Compact JSON: no spaces are emitted by the official-app-compatible body.
    assert " " not in call["data"]
    assert client.access_token == access
    assert client.refresh_token == "new-refresh"
    assert client.client_id == DEFAULT_OAUTH_CLIENT_ID


@pytest.mark.asyncio
async def test_login_allows_explicit_client_id_override():
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "access_token": "opaque-access-token",
                    "refresh_token": "new-refresh",
                },
            )
        ]
    )

    client = await SyphereApiClient.async_login(
        session,
        base_url="https://example.invalid:9997/",
        email="person@example.invalid",
        password="secret-placeholder",
        client_id=" explicit-client ",
    )

    assert json.loads(session.calls[0]["data"])["client_id"] == "explicit-client"
    assert client.client_id == "explicit-client"


@pytest.mark.asyncio
async def test_login_failure_does_not_echo_credentials_in_exception():
    session = FakeSession([FakeResponse(401, {"error": "bad credentials"})])

    with pytest.raises(SyphereAuthError) as exc_info:
        await SyphereApiClient.async_login(
            session,
            base_url="https://example.invalid:9997",
            email="person@example.invalid",
            password="super-secret-placeholder",
        )

    message = str(exc_info.value)
    assert "person@example.invalid" not in message
    assert "super-secret-placeholder" not in message


@pytest.mark.asyncio
async def test_status_exposes_only_explicit_pin_fields():
    session = FakeSession(
        [FakeResponse(200, {
            "delivery": {
                "has_delivery": True,
                "fix_lockbox": False,
                "delivery_pin": "001234",
            },
            "surname": "Example",
            "name": "Person",
            "personal_pin": "9876",
            "bt_ident": "PRIVATE-BT-IDENTIFIER",
            "deposition": {
                "state": "requested", "size": "M",
                "deposition_id": 42,
                "return_pin": "000567",
            },
            "deposition_active": True,
            "bt_reachability": False,
        })]
    )
    status = await make_client(session).async_get_status()
    assert status["delivery"]["delivery_pin"] == "001234"
    assert status["deposition"]["return_pin"] == "000567"
    assert status["personal_pin"] == "9876"
    assert "PRIVATE-BT-IDENTIFIER" not in repr(status)
    assert "Example" not in repr(status)
    assert status["deposition"].get("deposition_id") is None
    assert "delivery_pin" in status["api_field_names"]["delivery"]
    assert "return_pin" in status["api_field_names"]["deposition"]


@pytest.mark.asyncio
async def test_sizes_are_dynamic_and_ids_are_not_exposed():
    session = FakeSession(
        [
            FakeResponse(
                200,
                [
                    {"size": "XS", "available": True, "id": 101, "state": "x"},
                    {"size": "CUSTOM", "available": False, "id": 102, "state": "y"},
                ],
            )
        ]
    )
    sizes = await make_client(session).async_get_sizes()
    assert sizes == [
        {"size": "XS", "available": True, "state": "x"},
        {"size": "CUSTOM", "available": False, "state": "y"},
    ]
    assert "id" not in repr(sizes)


@pytest.mark.asyncio
async def test_reservation_uses_fresh_backend_id_for_selected_size():
    session = FakeSession(
        [
            FakeResponse(
                200,
                [
                    {"size": "S", "available": True, "id": 501},
                    {"size": "M", "available": True, "id": 777},
                ],
            ),
            FakeResponse(200, {"deposition_id": 9001}),
        ]
    )
    result = await make_client(session).async_reserve_size("M")

    assert result == {"deposition_id": 9001}
    assert session.calls[1]["json"] == {"lockbox_id": 777}
    assert session.calls[1]["url"].endswith("/api/deposition/reservation")


@pytest.mark.asyncio
async def test_cancel_uses_current_deposition_id():
    session = FakeSession(
        [
            FakeResponse(200, {"deposition": {"state": "requested", "deposition_id": 3456}}),
            FakeResponse(200, None),
        ]
    )
    await make_client(session).async_cancel_deposition()
    assert session.calls[1]["json"] == {"deposition_id": 3456}
    assert session.calls[1]["url"].endswith("/api/deposition/cancel")


@pytest.mark.asyncio
async def test_401_refreshes_tokens_and_retries_without_leaking_values():
    updated = []

    async def callback(tokens):
        updated.append(tokens)

    session = FakeSession(
        [
            FakeResponse(401, None),
            FakeResponse(
                200,
                {"access_token": "new-access", "refresh_token": "new-refresh"},
            ),
            FakeResponse(
                200,
                {"delivery": {}, "deposition": {}, "deposition_active": False},
            ),
        ]
    )
    client = make_client(session, callback)
    await client.async_get_status()

    assert client.access_token == "new-access"
    assert client.refresh_token == "new-refresh"
    assert updated == [{"access_token": "new-access", "refresh_token": "new-refresh"}]
    assert session.calls[1]["url"].endswith("/api/oauth/token")
    assert session.calls[1]["json"]["grant_type"] == "refresh_token"
    assert session.calls[2]["headers"]["Authorization"] == "Bearer new-access"


@pytest.mark.asyncio
async def test_pins_clear_when_parcel_or_deposition_is_not_active():
    session = FakeSession([FakeResponse(200, {
        "delivery": {"has_delivery": False, "delivery_pin": "1234"},
        "deposition": {"state": "no_deposition", "return_pin": "5678"},
        "deposition_active": False,
    })])
    status = await make_client(session).async_get_status()
    assert status["delivery"]["delivery_pin"] is None
    assert status["deposition"]["return_pin"] is None
    assert status["personal_pin"] is None


@pytest.mark.asyncio
async def test_pin_fallback_fields_when_returned_by_api():
    session = FakeSession([FakeResponse(200, {
        "delivery": {"has_delivery": True, "pickup_pin": "000777"},
        "deposition": {"state": "requested", "deposition_pin": 98765},
        "deposition_active": True,
    })])
    status = await make_client(session).async_get_status()
    assert status["delivery"]["delivery_pin"] == "000777"
    assert status["deposition"]["return_pin"] == "98765"
