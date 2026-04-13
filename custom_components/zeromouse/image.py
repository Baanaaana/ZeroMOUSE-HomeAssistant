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

NUM_IMAGES = 8


class ZeromouseEventImage(ZeromouseEntity, ImageEntity):
    """Image entity showing a detection event photo.

    If `index` is None, this is the title image (backward compat).
    Otherwise, it is the image at position `index` (0-7) in the event's image list.
    """

    def __init__(
        self,
        coordinator,
        device_id,
        device_name,
        session,
        index: int | None = None,
    ) -> None:
        ZeromouseEntity.__init__(self, coordinator, device_id, device_name)
        ImageEntity.__init__(self, coordinator.hass)
        self._session = session
        self._index = index
        self._cached_key: tuple[str, int | None] | None = None
        self._cached_image: bytes | None = None

        if index is None:
            self._attr_unique_id = f"{device_id}_event_image"
            self._attr_translation_key = "event_image"
        else:
            self._attr_unique_id = f"{device_id}_event_image_{index + 1}"
            self._attr_translation_key = f"event_image_{index + 1}"

    @property
    def image_last_updated(self) -> datetime | None:
        """Return when the image was last updated."""
        if self.coordinator.data and self.coordinator.data.get("time"):
            try:
                return datetime.fromisoformat(self.coordinator.data["time"])
            except (ValueError, TypeError):
                return None
        return None

    def _get_url(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        if self._index is None:
            return data.get("image_url") or None
        urls = data.get("image_urls") or []
        if self._index < len(urls):
            return urls[self._index] or None
        return None

    async def async_image(self) -> bytes | None:
        """Fetch the event image bytes from S3 via pre-signed URL."""
        url = self._get_url()
        if not url:
            return None

        data = self.coordinator.data or {}
        event_id = data.get("event_id")
        cache_key = (event_id, self._index)

        # Return cached image if same event and index
        if cache_key == self._cached_key and self._cached_image:
            return self._cached_image

        try:
            _LOGGER.debug("Fetching event image %s from S3", self._index)
            async with self._session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    _LOGGER.error(
                        "Failed to fetch event image (HTTP %s)",
                        resp.status,
                    )
                    return self._cached_image  # Return stale image on error
                self._cached_image = await resp.read()
                self._cached_key = cache_key
                return self._cached_image
        except Exception:
            _LOGGER.exception("Error fetching event image")
            return self._cached_image


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZeroMOUSE image entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    event_coord = data[DATA_EVENT_COORDINATOR]
    device_id = entry.data[CONF_DEVICE_ID]
    device_name = entry.data.get(CONF_DEVICE_NAME, "ZeroMOUSE")
    session = async_get_clientsession(hass)

    entities: list[ZeromouseEventImage] = [
        # Title image (backward compat)
        ZeromouseEventImage(event_coord, device_id, device_name, session, index=None),
    ]
    # 8 indexed images
    for i in range(NUM_IMAGES):
        entities.append(
            ZeromouseEventImage(event_coord, device_id, device_name, session, index=i)
        )

    async_add_entities(entities)
