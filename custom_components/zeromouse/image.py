"""Image platform for ZeroMOUSE integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_ID, CONF_DEVICE_NAME, DATA_EVENT_COORDINATOR, DOMAIN
from .entity import ZeromouseEntity


class ZeromouseEventImage(ZeromouseEntity, ImageEntity):
    """Image entity showing the latest detection event photo."""

    _attr_translation_key = "event_image"

    def __init__(self, coordinator, device_id, device_name) -> None:
        super().__init__(coordinator, device_id, device_name)
        self._attr_unique_id = f"{device_id}_event_image"

    @property
    def image_url(self) -> str | None:
        """Return the pre-signed S3 URL for the latest event image."""
        if self.coordinator.data and self.coordinator.data.get("image_url"):
            return self.coordinator.data["image_url"]
        return None

    @property
    def image_last_updated(self) -> datetime | None:
        """Return when the image was last updated (event timestamp)."""
        if self.coordinator.data and self.coordinator.data.get("time"):
            try:
                return datetime.fromisoformat(self.coordinator.data["time"])
            except (ValueError, TypeError):
                return None
        return None


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

    async_add_entities([ZeromouseEventImage(event_coord, device_id, device_name)])
