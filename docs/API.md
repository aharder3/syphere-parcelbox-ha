# Observed Syphere Parcelbox API

These endpoints were observed from authorized use of the official Syphere Parcelbox app. They are undocumented and may change.

Base URL used by the tested service:

```text
https://pbb.syphere.net:9997
```

## Credential login

The v0.2.0 integration uses the token endpoint for initial email/password login:

```http
POST /api/oauth/token
Content-Type: application/json
```

Implemented request shape:

```json
{
  "username": "user@example.invalid",
  "password": "<password>",
  "grant_type": "password",
  "scope": "openid"
}
```

If a deployment requires a Client ID at initial login, the optional field is added:

```json
{
  "client_id": "<client-id>"
}
```

The password is never persisted by the Home Assistant integration. If the token response does not directly include a Client ID, the integration attempts to read the `client_id` claim from the returned access-token JWT. This decode is only metadata extraction; it is not used to verify the JWT or make an authorization decision.

> The refresh flow below was directly observed. The exact initial credential request was not captured in the same session, so the credential-login shape remains experimental until verified on a live account.

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
