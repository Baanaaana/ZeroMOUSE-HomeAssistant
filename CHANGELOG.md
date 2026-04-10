# Changelog

## [1.1.0] - 2026-04-10

### Added
- **Email/password login** — log in with your ZeroMOUSE account directly, no mitmproxy or tokens needed
- **Automatic device discovery** — devices are found automatically after login
- **Event image entity** — latest detection photo displayed as a native HA image, proxied through HA
- **Device connected** binary sensor — shows if the device is online or offline
- **Diagnostic sensors** — last reset reason, MQTT error count, camera status, IR sensor status
- **Brand icons** — integration icon with light/dark mode support
- **Dashboard card** example in README
- **Mobile notification** automation example with timestamped image snapshots

### Fixed
- Cognito `application/x-amz-json-1.1` content type handling for aiohttp
- `ImageEntity` initialization for proper access token support
- Timestamp sensor returns `datetime` object instead of string

## [1.0.0] - 2026-04-09

### Added
- Initial release
- Cognito refresh token authentication
- Device shadow polling (10s interval)
- Event polling via GraphQL (60s interval)
- Binary sensors: flap blocked, prey blocking enabled
- Sensors: event count, PIR triggers, WiFi signal, boot count, firmware version, undecidable mode, block count, unblock count
- Event sensors: last event type, classification, time
- Config flow UI with credential validation
- Re-authentication flow for expired tokens
- HACS compatible
