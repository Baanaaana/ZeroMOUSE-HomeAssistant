"""Image platform for ZeroMOUSE integration."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_ID, CONF_DEVICE_NAME, DATA_EVENT_COORDINATOR, DOMAIN
from .entity import ZeromouseEntity

_LOGGER = logging.getLogger(__name__)


class ZeromouseEventImage(ZeromouseEntity, ImageEntity):
    """Image entity showing the latest detection event photo."""

    _attr_translation_key = "event_image"

    def __init__(self, coordinator, device_id, device_name, session) -> None:
        super().__init__(coordinator, device_id, device_name)
        self._attr_unique_id = f"{device_id}_event_image"
        self._session = session
        self._cached_event_id: str | None = None
        self._cached_image: bytes | None = None

    @property
    def image_last_updated(self) -> datetime | None:
        """Return when the image was last updated."""
        if self.coordinator.data and self.coordinator.data.get("time"):
            try:
                return datetime.fromisoformat(self.coordinator.data["time"])
            except (ValueError, TypeError):
                return None
        return None

    async def async_image(self) -> bytes | None:
        """Fetch the event image bytes from S3 via pre-signed URL."""
        data = self.coordinator.data
        if not data:
            return None

        image_url = data.get("image_url")
        event_id = data.get("event_id")

        if not image_url:
            _LOGGER.debug("No image URL available for event")
            return None

        # Return cached image if same event
        if event_id and event_id == self._cached_event_id and self._cached_image:
            return self._cached_image

        try:
            _LOGGER.debug("Fetching event image from S3")
            async with self._session.get(image_url, timeout=15) as resp:
                if resp.status != 200:
                    _LOGGER.error(
                        "Failed to fetch event image (HTTP %s): %s",
                        resp.status,
                        await resp.text()[:200] if resp.status != 200 else "",
                    )
                    return self._cached_image  # Return stale image on error
                self._cached_image = await resp.read()
                self._cached_event_id = event_id
                return self._cached_image
        except Exception:
            _LOGGER.exception("Error fetching event image")
            return self._cached_image


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZeroMOUSE image entity from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    event_coord = data[DATA_EVENT_COORDINATOR]
    device_id = entry.data[CONF_DEVICE_ID]
    device_name = entry.data.get(CONF_DEVICE_NAME, "ZeroMOUSE")
    session = async_get_clientsession(hass)

    async_add_entities([ZeromouseEventImage(event_coord, device_id, device_name, session)])
