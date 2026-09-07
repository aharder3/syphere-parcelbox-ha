# Observed Syphere Parcelbox API

These endpoints were observed from authorized use of the official Syphere Parcelbox app. They are undocumented and may change.

Base URL used by the tested service:

```text
https://pbb.syphere.net:9997
```

## Credential login

The initial email/password request below was captured from the official iOS app. The wire format is intentionally unusual and is reproduced exactly by the integration:

```http
POST /api/oauth/token
Content-Type: application/x-www-form-urlencoded
Accept: application/json, text/plain, */*
```

Despite the declared form content type, the body is a **raw compact JSON string**, not standard `key=value` form data:

```json
{"username":"user@example.invalid","password":"<password>","grant_type":"password","client_id":"<official-app-client-id>"}
```

There is no bearer `Authorization` header on the initial password login. The official app OAuth Client ID is an application identifier (not a client secret) and is supplied automatically by the integration. The password is used only for this exchange and is never persisted in the Home Assistant config entry.

## Authenticated requests

Authenticated requests use:

```http
Authorization: Bearer <access-token>
Accept: application/json
```

## Status

```http
GET /api/user/homepage
```

The raw response can contain personal data and PINs. The integration only retains these non-sensitive fields:

```json
{
  "delivery": {
    "has_delivery": true,
    "fix_lockbox": false
  },
  "deposition": {
    "state": "no_deposition"
  },
  "deposition_active": true,
  "bt_reachability": false
}
```

## Available deposition sizes

```http
GET /api/deposition/size
```

Synthetic example:

```json
[
  {"size": "S", "available": true, "id": 1001, "state": "someState"},
  {"size": "M", "available": true, "id": 1002, "state": "someState"},
  {"size": "L", "available": false, "id": 1003, "state": "someState"}
]
```

Size labels are treated as dynamic strings. Backend IDs are used only transiently for the immediately following reservation request.

## Reserve deposition

```http
POST /api/deposition/reservation
Content-Type: application/json
```

```json
{"lockbox_id": 1002}
```

Synthetic response:

```json
{"deposition_id": 2001}
```

## Cancel deposition

The integration first reads the current deposition ID from `/api/user/homepage`, then sends:

```http
POST /api/deposition/cancel
Content-Type: application/json
```

```json
{"deposition_id": 2001}
```

A successful observed response has HTTP 200 with an empty body.

## Open delivery compartment

```http
POST /api/delivery/open
Content-Type: application/json
```

```json
{}
```

A successful observed response has HTTP 200 with an empty body. The command requests a physical compartment to open and should be treated as a physical action.

## Refresh OAuth token

```http
POST /api/oauth/token
Authorization: Bearer <current-access-token>
Content-Type: application/json
```

```json
{
  "access_token": "<current-access-token>",
  "refresh_token": "<refresh-token>",
  "grant_type": "refresh_token",
  "client_id": "<client-id>"
}
```

The response contains a new access token and refresh token. The integration persists both into the Home Assistant config entry.
