"""Binary sensor platform for ZeroMOUSE integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_ID, CONF_DEVICE_NAME, DATA_SHADOW_COORDINATOR, DOMAIN
from .entity import ZeromouseEntity


@dataclass(frozen=True, kw_only=True)
class ZeromouseBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a ZeroMOUSE binary sensor."""

    value_fn: Callable[[dict], bool | None]


BINARY_SENSORS: tuple[ZeromouseBinarySensorDescription, ...] = (
    ZeromouseBinarySensorDescription(
        key="flap_blocked",
        translation_key="flap_blocked",
        device_class=BinarySensorDeviceClass.LOCK,
        value_fn=lambda d: not bool(d.get("rfid", {}).get("blockState", 0) & 1),
    ),
    ZeromouseBinarySensorDescription(
        key="blocking_enabled",
        translation_key="blocking_enabled",
        icon="mdi:shield-lock",
        value_fn=lambda d: bool(d.get("rfid", {}).get("blockEnabled", 0)),
    ),
    ZeromouseBinarySensorDescription(
        key="device_connected",
        translation_key="device_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("_connectivity", {}).get("connected"),
    ),
)


class ZeromouseBinarySensor(ZeromouseEntity, BinarySensorEntity):
    """A binary sensor from the device shadow."""

    entity_description: ZeromouseBinarySensorDescription

    def __init__(self, coordinator, description, device_id, device_name) -> None:
        super().__init__(coordinator, device_id, device_name)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZeroMOUSE binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    shadow_coord = data[DATA_SHADOW_COORDINATOR]
    device_id = entry.data[CONF_DEVICE_ID]
    device_name = entry.data.get(CONF_DEVICE_NAME, "ZeroMOUSE")

    async_add_entities(
        ZeromouseBinarySensor(shadow_coord, desc, device_id, device_name)
        for desc in BINARY_SENSORS
    )
