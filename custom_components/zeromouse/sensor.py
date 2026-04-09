"""Sensor platform for ZeroMOUSE integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfSignalStrength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    DATA_EVENT_COORDINATOR,
    DATA_SHADOW_COORDINATOR,
    DOMAIN,
)
from .entity import ZeromouseEntity


@dataclass(frozen=True, kw_only=True)
class ZeromouseShadowSensorDescription(SensorEntityDescription):
    """Describes a sensor derived from the device shadow."""

    value_fn: Callable[[dict], Any]


@dataclass(frozen=True, kw_only=True)
class ZeromouseEventSensorDescription(SensorEntityDescription):
    """Describes a sensor derived from detection events."""

    value_fn: Callable[[dict | None], Any]


SHADOW_SENSORS: tuple[ZeromouseShadowSensorDescription, ...] = (
    ZeromouseShadowSensorDescription(
        key="event_count",
        translation_key="event_count",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("system", {}).get("eventCount"),
    ),
    ZeromouseShadowSensorDescription(
        key="pir_triggers",
        translation_key="pir_triggers",
        icon="mdi:motion-sensor",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("system", {}).get("pirTriggerCount"),
    ),
    ZeromouseShadowSensorDescription(
        key="wifi_rssi",
        translation_key="wifi_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=UnitOfSignalStrength.DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("system", {}).get("metricWifiRSSI"),
    ),
    ZeromouseShadowSensorDescription(
        key="boot_count",
        translation_key="boot_count",
        icon="mdi:restart",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("system", {}).get("bootCount"),
    ),
    ZeromouseShadowSensorDescription(
        key="firmware",
        translation_key="firmware",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (
            f"{d['system']['verMajor']}.{d['system']['verMinor']}.{d['system']['verRevision']}"
            if "system" in d and "verMajor" in d.get("system", {})
            else None
        ),
    ),
    ZeromouseShadowSensorDescription(
        key="undecidable_mode",
        translation_key="undecidable_mode",
        icon="mdi:help-circle-outline",
        value_fn=lambda d: {0: "default", 1: "allow", 2: "block"}.get(
            d.get("system", {}).get("undecidableMode"), "unknown"
        ),
    ),
    ZeromouseShadowSensorDescription(
        key="block_count",
        translation_key="block_count",
        icon="mdi:door-closed-lock",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("rfid", {}).get("blockCount"),
    ),
    ZeromouseShadowSensorDescription(
        key="unblock_count",
        translation_key="unblock_count",
        icon="mdi:door-open",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("rfid", {}).get("unblockCount"),
    ),
)

EVENT_SENSORS: tuple[ZeromouseEventSensorDescription, ...] = (
    ZeromouseEventSensorDescription(
        key="last_event_type",
        translation_key="last_event_type",
        icon="mdi:cat",
        value_fn=lambda d: d.get("type") if d else None,
    ),
    ZeromouseEventSensorDescription(
        key="last_event_classification",
        translation_key="last_event_classification",
        icon="mdi:eye-check",
        value_fn=lambda d: d.get("classification") if d else None,
    ),
    ZeromouseEventSensorDescription(
        key="last_event_time",
        translation_key="last_event_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.get("time") if d else None,
    ),
    ZeromouseEventSensorDescription(
        key="last_event_image",
        translation_key="last_event_image",
        icon="mdi:camera",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("image_url") if d else None,
    ),
)


class ZeromouseShadowSensor(ZeromouseEntity, SensorEntity):
    """A sensor that reads from the device shadow."""

    entity_description: ZeromouseShadowSensorDescription

    def __init__(self, coordinator, description, device_id, device_name) -> None:
        super().__init__(coordinator, device_id, device_name)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class ZeromouseEventSensor(ZeromouseEntity, SensorEntity):
    """A sensor that reads from detection events."""

    entity_description: ZeromouseEventSensorDescription

    def __init__(self, coordinator, description, device_id, device_name) -> None:
        super().__init__(coordinator, device_id, device_name)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZeroMOUSE sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    shadow_coord = data[DATA_SHADOW_COORDINATOR]
    event_coord = data[DATA_EVENT_COORDINATOR]
    device_id = entry.data[CONF_DEVICE_ID]
    device_name = entry.data.get(CONF_DEVICE_NAME, "ZeroMOUSE")

    entities: list[SensorEntity] = []

    for desc in SHADOW_SENSORS:
        entities.append(
            ZeromouseShadowSensor(shadow_coord, desc, device_id, device_name)
        )

    for desc in EVENT_SENSORS:
        entities.append(
            ZeromouseEventSensor(event_coord, desc, device_id, device_name)
        )

    async_add_entities(entities)
