#!/usr/bin/env python3
"""
ZeroMOUSE → Home Assistant Bridge

Polls the ZeroMOUSE cloud API and publishes state to a local MQTT broker
with Home Assistant auto-discovery.
"""

import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

import requests
import paho.mqtt.client as mqtt
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("zeromouse")

shutdown = Event()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Cognito Auth
# ---------------------------------------------------------------------------

class CognitoAuth:
    """Handles Cognito token refresh using the captured refresh token."""

    def __init__(self, cfg: dict):
        self.region = cfg["region"]
        self.client_id = cfg["client_id"]
        self.refresh_token = cfg["refresh_token"]
        self.endpoint = f"https://cognito-idp.{self.region}.amazonaws.com/"
        self.id_token = None
        self.access_token = None
        self.token_expiry = 0

    def ensure_valid_token(self):
        if time.time() < self.token_expiry - 60:
            return
        self._refresh()

    def _refresh(self):
        log.info("Refreshing Cognito tokens")
        resp = requests.post(
            self.endpoint,
            headers={
                "Content-Type": "application/x-amz-json-1.1",
                "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
            },
            json={
                "ClientId": self.client_id,
                "AuthFlow": "REFRESH_TOKEN_AUTH",
                "AuthParameters": {
                    "REFRESH_TOKEN": self.refresh_token,
                },
            },
        )
        resp.raise_for_status()
        result = resp.json()["AuthenticationResult"]
        self.id_token = result["IdToken"]
        self.access_token = result["AccessToken"]
        self.token_expiry = time.time() + result["ExpiresIn"]
        log.info("Tokens refreshed, valid for %ds", result["ExpiresIn"])


# ---------------------------------------------------------------------------
# Shadow API
# ---------------------------------------------------------------------------

class ShadowClient:
    """Fetches device shadow state via the REST API."""

    def __init__(self, cfg: dict, auth: CognitoAuth):
        self.url = cfg["api"]["shadow_url"]
        self.device_id = cfg["device"]["id"]
        self.auth = auth

    def get_shadow(self) -> dict | None:
        self.auth.ensure_valid_token()
        try:
            resp = requests.get(
                self.url,
                params={"deviceID": self.device_id},
                headers={"auth-token": self.auth.id_token},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            log.error("Shadow API error: %s", e)
            return None


# ---------------------------------------------------------------------------
# GraphQL Event Client
# ---------------------------------------------------------------------------

EVENT_QUERY = """
query listMbrPtfEventDataWithImages(
  $deviceID: String!,
  $sortDirection: ModelSortDirection,
  $filter: ModelMbrPtfEventDataFilterInput,
  $limit: Int
) {
  listEventbyDeviceChrono(
    deviceID: $deviceID,
    sortDirection: $sortDirection,
    filter: $filter,
    limit: $limit
  ) {
    items {
      eventID
      eventTime
      type
      classification_byNet
      catClusterId
      isSeen
      isFlagged
      titleImageIndex
      createdAt
      Images {
        items {
          filePath
        }
      }
    }
  }
}
"""


class EventClient:
    """Fetches recent detection events via the AppSync GraphQL API."""

    def __init__(self, cfg: dict, auth: CognitoAuth):
        self.url = cfg["api"]["graphql_url"]
        self.device_id = cfg["device"]["id"]
        self.s3_bucket = "mbr-ptf-images-eu-central-1-dev"
        self.auth = auth
        self.last_event_id = None

    def get_latest_events(self, limit: int = 5) -> list[dict]:
        self.auth.ensure_valid_token()
        try:
            resp = requests.post(
                self.url,
                headers={
                    "Authorization": self.auth.id_token,
                    "Content-Type": "application/json",
                },
                json={
                    "query": EVENT_QUERY,
                    "variables": {
                        "deviceID": self.device_id,
                        "limit": limit,
                        "sortDirection": "DESC",
                        "filter": {
                            "classification_byNet": {"ne": "free"},
                        },
                    },
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            items = data.get("listEventbyDeviceChrono", {}).get("items", [])
            return items
        except requests.RequestException as e:
            log.error("GraphQL event query error: %s", e)
            return []

    def get_image_url(self, file_path: str) -> str:
        return f"https://{self.s3_bucket}.s3.eu-central-1.amazonaws.com/private/{file_path}"


# ---------------------------------------------------------------------------
# HA MQTT Publisher
# ---------------------------------------------------------------------------

class HAPublisher:
    """Publishes state and auto-discovery messages to MQTT."""

    def __init__(self, cfg: dict):
        self.device_id = cfg["device"]["id"]
        self.device_name = cfg["device"].get("name", "ZeroMOUSE")
        self.client = mqtt.Client(
            client_id=f"zeromouse-bridge-{self.device_id[:8]}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        mqtt_cfg = cfg["mqtt"]
        if mqtt_cfg.get("username"):
            self.client.username_pw_set(mqtt_cfg["username"], mqtt_cfg.get("password", ""))
        self.client.will_set(
            f"zeromouse/{self.device_id}/availability",
            "offline",
            retain=True,
        )
        self.client.connect(mqtt_cfg["host"], mqtt_cfg.get("port", 1883))
        self.client.loop_start()
        self._discovery_sent = False

    def _device_info(self) -> dict:
        return {
            "identifiers": [f"zeromouse_{self.device_id}"],
            "name": self.device_name,
            "manufacturer": "ZeroMOUSE",
            "model": "ZeroMOUSE 2.0",
            "sw_version": None,  # filled from shadow
        }

    def send_discovery(self, shadow: dict):
        if self._discovery_sent:
            return

        reported = shadow.get("state", {}).get("reported", {})
        sys_data = reported.get("system", {})
        sw = f"{sys_data.get('verMajor', 0)}.{sys_data.get('verMinor', 0)}.{sys_data.get('verRevision', 0)}"

        device_info = self._device_info()
        device_info["sw_version"] = sw

        avail = {
            "topic": f"zeromouse/{self.device_id}/availability",
            "payload_available": "online",
            "payload_not_available": "offline",
        }

        prefix = f"zeromouse/{self.device_id}"
        disc_prefix = f"homeassistant"
        uid_prefix = f"zeromouse_{self.device_id}"

        entities = [
            # Binary sensors
            {
                "component": "binary_sensor",
                "key": "flap_blocked",
                "config": {
                    "name": "Flap Blocked",
                    "device_class": "lock",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{{ 'ON' if value_json.rfid.blockState | bitwise_and(1) else 'OFF' }}",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                },
            },
            {
                "component": "binary_sensor",
                "key": "blocking_enabled",
                "config": {
                    "name": "Prey Blocking Enabled",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{{ 'ON' if value_json.rfid.blockEnabled else 'OFF' }}",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                },
            },
            # Sensors
            {
                "component": "sensor",
                "key": "event_count",
                "config": {
                    "name": "Event Count",
                    "icon": "mdi:counter",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{{ value_json.system.eventCount }}",
                    "state_class": "total_increasing",
                },
            },
            {
                "component": "sensor",
                "key": "pir_triggers",
                "config": {
                    "name": "PIR Triggers",
                    "icon": "mdi:motion-sensor",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{{ value_json.system.pirTriggerCount }}",
                    "state_class": "total_increasing",
                },
            },
            {
                "component": "sensor",
                "key": "wifi_rssi",
                "config": {
                    "name": "WiFi Signal",
                    "device_class": "signal_strength",
                    "unit_of_measurement": "dBm",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{{ value_json.system.metricWifiRSSI }}",
                    "entity_category": "diagnostic",
                },
            },
            {
                "component": "sensor",
                "key": "boot_count",
                "config": {
                    "name": "Boot Count",
                    "icon": "mdi:restart",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{{ value_json.system.bootCount }}",
                    "entity_category": "diagnostic",
                    "state_class": "total_increasing",
                },
            },
            {
                "component": "sensor",
                "key": "firmware",
                "config": {
                    "name": "Firmware Version",
                    "icon": "mdi:chip",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{{ value_json.system.verMajor }}.{{ value_json.system.verMinor }}.{{ value_json.system.verRevision }}",
                    "entity_category": "diagnostic",
                },
            },
            {
                "component": "sensor",
                "key": "undecidable_mode",
                "config": {
                    "name": "Undecidable Mode",
                    "icon": "mdi:help-circle-outline",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{% set m = value_json.system.undecidableMode %}{% if m == 0 %}default{% elif m == 1 %}allow{% elif m == 2 %}block{% else %}unknown{% endif %}",
                },
            },
            {
                "component": "sensor",
                "key": "block_count",
                "config": {
                    "name": "Block Count",
                    "icon": "mdi:door-closed-lock",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{{ value_json.rfid.blockCount }}",
                    "state_class": "total_increasing",
                },
            },
            {
                "component": "sensor",
                "key": "unblock_count",
                "config": {
                    "name": "Unblock Count",
                    "icon": "mdi:door-open",
                    "state_topic": f"{prefix}/state",
                    "value_template": "{{ value_json.rfid.unblockCount }}",
                    "state_class": "total_increasing",
                },
            },
            # Event sensors
            {
                "component": "sensor",
                "key": "last_event_type",
                "config": {
                    "name": "Last Event Type",
                    "icon": "mdi:cat",
                    "state_topic": f"{prefix}/last_event",
                    "value_template": "{{ value_json.type }}",
                },
            },
            {
                "component": "sensor",
                "key": "last_event_classification",
                "config": {
                    "name": "Last Event Classification",
                    "icon": "mdi:eye-check",
                    "state_topic": f"{prefix}/last_event",
                    "value_template": "{{ value_json.classification }}",
                },
            },
            {
                "component": "sensor",
                "key": "last_event_time",
                "config": {
                    "name": "Last Event Time",
                    "device_class": "timestamp",
                    "state_topic": f"{prefix}/last_event",
                    "value_template": "{{ value_json.time }}",
                },
            },
            {
                "component": "sensor",
                "key": "last_event_image",
                "config": {
                    "name": "Last Event Image",
                    "icon": "mdi:camera",
                    "state_topic": f"{prefix}/last_event",
                    "value_template": "{{ value_json.image_url }}",
                    "entity_category": "diagnostic",
                },
            },
        ]

        for ent in entities:
            topic = f"{disc_prefix}/{ent['component']}/{uid_prefix}/{ent['key']}/config"
            payload = {
                "unique_id": f"{uid_prefix}_{ent['key']}",
                "object_id": f"zeromouse_{ent['key']}",
                "device": device_info,
                "availability": avail,
                **ent["config"],
            }
            self.client.publish(topic, json.dumps(payload), retain=True)

        log.info("Published HA discovery for %d entities", len(entities))
        self._discovery_sent = True

    def publish_state(self, shadow: dict):
        reported = shadow.get("state", {}).get("reported", {})
        self.client.publish(
            f"zeromouse/{self.device_id}/state",
            json.dumps(reported),
            retain=True,
        )

    def publish_event(self, event: dict):
        self.client.publish(
            f"zeromouse/{self.device_id}/last_event",
            json.dumps(event),
            retain=True,
        )

    def set_available(self, available: bool = True):
        self.client.publish(
            f"zeromouse/{self.device_id}/availability",
            "online" if available else "offline",
            retain=True,
        )

    def disconnect(self):
        self.set_available(False)
        self.client.loop_stop()
        self.client.disconnect()


# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

def run(config_path: str = "config.yaml"):
    cfg = load_config(config_path)

    auth = CognitoAuth(cfg["cognito"])
    shadow_client = ShadowClient(cfg, auth)
    event_client = EventClient(cfg, auth)
    publisher = HAPublisher(cfg)

    shadow_interval = cfg["polling"]["shadow_interval"]
    event_interval = cfg["polling"]["event_interval"]

    last_shadow_poll = 0
    last_event_poll = 0
    last_event_id = None

    def on_shutdown(sig, frame):
        log.info("Shutting down")
        shutdown.set()

    signal.signal(signal.SIGINT, on_shutdown)
    signal.signal(signal.SIGTERM, on_shutdown)

    log.info("ZeroMOUSE bridge starting for device %s", cfg["device"]["id"])

    # Initial token fetch
    try:
        auth.ensure_valid_token()
    except Exception as e:
        log.error("Initial auth failed: %s", e)
        log.error("Check your refresh_token in config.yaml. It may have expired — re-capture via mitmproxy.")
        sys.exit(1)

    publisher.set_available(True)

    while not shutdown.is_set():
        now = time.time()

        # Shadow poll
        if now - last_shadow_poll >= shadow_interval:
            last_shadow_poll = now
            shadow = shadow_client.get_shadow()
            if shadow:
                publisher.send_discovery(shadow)
                publisher.publish_state(shadow)
                log.debug("Shadow published")

        # Event poll
        if now - last_event_poll >= event_interval:
            last_event_poll = now
            events = event_client.get_latest_events(limit=1)
            if events:
                ev = events[0]
                if ev["eventID"] != last_event_id:
                    last_event_id = ev["eventID"]
                    # Build image URL from first image
                    image_url = ""
                    images = ev.get("Images", {})
                    if images and images.get("items"):
                        image_url = event_client.get_image_url(
                            images["items"][0]["filePath"]
                        )
                    event_payload = {
                        "event_id": ev["eventID"],
                        "type": ev.get("type", "unknown"),
                        "classification": ev.get("classification_byNet", "unknown"),
                        "time": datetime.fromtimestamp(
                            ev["eventTime"], tz=timezone.utc
                        ).isoformat(),
                        "image_url": image_url,
                        "cat_cluster_id": ev.get("catClusterId"),
                    }
                    publisher.publish_event(event_payload)
                    log.info(
                        "New event: %s (%s) at %s",
                        event_payload["type"],
                        event_payload["classification"],
                        event_payload["time"],
                    )

        shutdown.wait(1)

    publisher.disconnect()
    log.info("Bridge stopped")


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    run(config_file)
