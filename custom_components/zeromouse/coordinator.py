"""DataUpdateCoordinators for ZeroMOUSE shadow and event polling."""

import logging
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EventClient, ShadowClient, ZeromouseApiError, ZeromouseAuthError
from .const import EVENT_SCAN_INTERVAL, SHADOW_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ZeromouseShadowCoordinator(DataUpdateCoordinator[dict]):
    """Polls the device shadow REST API."""

    def __init__(self, hass: HomeAssistant, client: ShadowClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="ZeroMOUSE Shadow",
            update_interval=SHADOW_SCAN_INTERVAL,
        )
        self._client = client

    async def _async_update_data(self) -> dict:
        try:
            shadow = await self._client.async_get_shadow()
        except ZeromouseAuthError as err:
            raise ConfigEntryAuthFailed(
                "Refresh token expired — re-capture via mitmproxy"
            ) from err
        except ZeromouseApiError as err:
            raise UpdateFailed(f"Shadow API error: {err}") from err

        return shadow.get("state", {}).get("reported", {})


class ZeromouseEventCoordinator(DataUpdateCoordinator[dict | None]):
    """Polls the GraphQL API for detection events."""

    def __init__(self, hass: HomeAssistant, client: EventClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="ZeroMOUSE Events",
            update_interval=EVENT_SCAN_INTERVAL,
        )
        self._client = client

    async def _async_update_data(self) -> dict | None:
        try:
            events = await self._client.async_get_latest_events(limit=1)
        except ZeromouseAuthError as err:
            raise ConfigEntryAuthFailed(
                "Refresh token expired — re-capture via mitmproxy"
            ) from err
        except ZeromouseApiError as err:
            raise UpdateFailed(f"Event API error: {err}") from err

        if not events:
            return self.data  # Keep previous data

        ev = events[0]

        # Build image URL from title image
        image_url = ""
        images = ev.get("Images") or {}
        items = images.get("items") or []
        if items:
            title_idx = ev.get("titleImageIndex", 0) or 0
            idx = title_idx if title_idx < len(items) else 0
            file_path = items[idx]["filePath"]
            image_url = self._client.get_image_url(file_path)
            if image_url:
                _LOGGER.debug("Event image URL generated for %s", file_path)
            else:
                _LOGGER.warning("Failed to generate image URL for %s (missing AWS credentials?)", file_path)

        return {
            "event_id": ev["eventID"],
            "type": ev.get("type", "unknown"),
            "classification": ev.get("classification_byNet", "unknown"),
            "time": datetime.fromtimestamp(
                ev["eventTime"], tz=timezone.utc
            ).isoformat(),
            "image_url": image_url,
            "cat_cluster_id": ev.get("catClusterId"),
        }
