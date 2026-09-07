# Changelog

## v0.2.1 — Credential Login Fix

- Match the official iOS app login wire format exactly.
- Send compact raw JSON while declaring `application/x-www-form-urlencoded`.
- Include the official app OAuth Client ID automatically.
- Remove the Client ID field from normal Home Assistant setup.
- Keep passwords out of persisted config entries.
- Update tests to verify the observed request shape.

## v0.2.0 — Credential Login

- Add direct Syphere email/password login through `/api/oauth/token`.
- Do not persist the Syphere password after the initial token exchange.
- Automatically derive `client_id` from the returned access-token JWT when possible.
- Keep an optional Client ID setup field for Syphere deployments that require it during the initial login request.
- Keep automatic access/refresh-token rotation.
- Keep dynamic parcel-compartment size discovery and all v0.1 control/status features.
- Redact the configured account email from Home Assistant diagnostics.

## v0.1.0 — API Foundation

- Initial reverse-engineered API client.
- Status polling, dynamic compartment sizes, deposition reservation/cancel and delivery open.
- Token refresh and privacy-minimized diagnostics.
