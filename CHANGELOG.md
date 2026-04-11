# Changelog

## [1.2.1] - 2026-04-11

### Changed
- **Event polling interval** reduced to 30 seconds for faster event detection

## [1.2.0] - 2026-04-11

### Added
- **Dutch notification template** — `ha_notification_nl.yaml` for Dutch-speaking users
- **Cat name variable** in notification automation — personalized messages like "Milo tried to bring in prey"
- **Smart notification messages** — context-aware text per classification (prey, clean, out, undecidable, etc.)
- **Critical alerts only for prey/undecidable** — other events use normal notification priority

### Fixed
- **Flap blocked sensor inverted** — `BinarySensorDeviceClass.LOCK` semantics were backwards; now correctly shows "Locked" when prey blocking is active
- **Notification trigger** — changed from `last_event_type` to `last_event_time` for reliable firing on new events

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
