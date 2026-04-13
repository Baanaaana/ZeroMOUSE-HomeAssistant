# ZeroMOUSE Home Assistant Integration

<p align="center">
  <img src="zeromouse_logo.svg" alt="ZeroMOUSE logo" width="200">
</p>

> **Disclaimer:** This is an **unofficial**, community-developed integration. It is **not** created, endorsed, or supported by ZeroMOUSE or its parent company. The ZeroMOUSE name and logo are trademarks of their respective owners and are used here solely for identification purposes. This project has no affiliation with ZeroMOUSE.


A custom [Home Assistant](https://www.home-assistant.io/) integration for the **ZeroMOUSE** smart pet door. Monitor your cat flap status, detection events, and view captured images — all from your Home Assistant dashboard.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Baanaaana&repository=ZeroMOUSE-HomeAssistant&category=integration)

Or manually:

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the **three-dot menu** → **Custom repositories**
3. Add this repository URL with category **Integration**
4. Search for **ZeroMOUSE** and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/zeromouse` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Features

- **Email/password login** — use your existing ZeroMOUSE account, no tokens or technical setup required
- **Auto-discovery** — your devices are found automatically after login
- **Live status** — flap lock state, prey blocking, event counts, WiFi signal, device connectivity
- **Detection events** — last event type, classification (prey/clean/test), timestamp
- **Event images** — latest detection photo displayed as a native HA image entity
- **HACS compatible** — easy install and updates

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Flap blocked | Binary sensor | Whether the flap is currently locked |
| Prey blocking enabled | Binary sensor | Whether prey blocking is active |
| Device connected | Binary sensor | Whether the device is online |
| Event count | Sensor | Total detection events |
| PIR triggers | Sensor | Total PIR motion triggers |
| Block count | Sensor | Times the flap was blocked |
| Unblock count | Sensor | Times the flap was unblocked |
| Last event type | Sensor | e.g. CAT_ENTERED |
| Last event classification | Sensor | e.g. clean, prey, test, out |
| Last event time | Sensor | Timestamp of the last detection |
| Undecidable mode | Sensor | How uncertain detections are handled |
| WiFi signal | Sensor | Device WiFi RSSI (dBm) |
| Boot count | Sensor | Device restart count |
| Firmware version | Sensor | Current firmware version |
| Last reset reason | Sensor | Why the device last rebooted (SW, WDT, etc.) |
| MQTT errors | Sensor | MQTT error count |
| Camera status | Sensor | Camera health (OK or Error) |
| IR sensor status | Sensor | IR sensor health (OK or Error) |
| Last event | Image | Photo from the latest detection event |

## Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **ZeroMOUSE**
3. Enter your ZeroMOUSE account **email** and **password** (same as the mobile app)
4. Your device is discovered automatically — done!

## Dashboard Card

Add this YAML to your dashboard for a ZeroMOUSE overview card (Edit Dashboard → Add Card → Manual):

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-title-card
    title: ZeroMOUSE
    subtitle: >
      {{ states('sensor.zeromouse_last_event_classification') | title }}
      — {{ relative_time(states.sensor.zeromouse_last_event_time.state | as_datetime) }} ago
  - type: custom:swipe-card
    parameters:
      pagination:
        type: bullets
      loop: true
      autoplay:
        delay: 3000
        disableOnInteraction: true
    cards:
      - type: picture-entity
        entity: image.zeromouse_event_image_1
        show_state: false
        show_name: false
        aspect_ratio: 4x3
      - type: picture-entity
        entity: image.zeromouse_event_image_2
        show_state: false
        show_name: false
        aspect_ratio: 4x3
      - type: picture-entity
        entity: image.zeromouse_event_image_3
        show_state: false
        show_name: false
        aspect_ratio: 4x3
      - type: picture-entity
        entity: image.zeromouse_event_image_4
        show_state: false
        show_name: false
        aspect_ratio: 4x3
      - type: picture-entity
        entity: image.zeromouse_event_image_5
        show_state: false
        show_name: false
        aspect_ratio: 4x3
      - type: picture-entity
        entity: image.zeromouse_event_image_6
        show_state: false
        show_name: false
        aspect_ratio: 4x3
      - type: picture-entity
        entity: image.zeromouse_event_image_7
        show_state: false
        show_name: false
        aspect_ratio: 4x3
      - type: picture-entity
        entity: image.zeromouse_event_image_8
        show_state: false
        show_name: false
        aspect_ratio: 4x3
  - type: horizontal-stack
    cards:
      - type: tile
        entity: binary_sensor.zeromouse_flap_blocked
        name: Flap
        color: red
        vertical: true
      - type: tile
        entity: binary_sensor.zeromouse_prey_blocking_enabled
        name: Blocking
        color: green
        vertical: true
      - type: tile
        entity: binary_sensor.zeromouse_device_connected
        name: Device
        color: blue
        vertical: true
  - type: entities
    entities:
      - entity: sensor.zeromouse_last_event_type
        name: Event Type
        icon: mdi:cat
      - entity: sensor.zeromouse_last_event_classification
        name: Classification
        icon: mdi:eye-check
      - entity: sensor.zeromouse_last_event_time
        name: Last Event
        icon: mdi:clock-outline
      - type: divider
      - entity: sensor.zeromouse_event_count
        name: Total Events
      - entity: sensor.zeromouse_pir_triggers
        name: PIR Triggers
      - entity: sensor.zeromouse_block_count
        name: Times Blocked
      - entity: sensor.zeromouse_unblock_count
        name: Times Unblocked
      - type: divider
      - entity: sensor.zeromouse_wifi_signal
        name: WiFi Signal
      - entity: sensor.zeromouse_firmware_version
        name: Firmware
```

> **Required custom cards (install via HACS → Frontend):**
> - [mushroom-cards](https://github.com/piitaya/lovelace-mushroom) for the title card
> - [swipe-card](https://github.com/bramkragten/swipe-card) for the image carousel
>
> **Fallback (no custom cards):** Replace `custom:mushroom-title-card` with a `markdown` card and `custom:swipe-card` with a single `picture-entity` pointing at `image.zeromouse_last_event`:
> ```yaml
> - type: markdown
>   content: |
>     ## ZeroMOUSE
>     {{ states('sensor.zeromouse_last_event_classification') | title }}
>     — {{ relative_time(states.sensor.zeromouse_last_event_time.state | as_datetime) }} ago
> - type: picture-entity
>   entity: image.zeromouse_last_event
>   show_state: false
>   show_name: false
>   aspect_ratio: 4x3
> ```
>
> Events have between 5-8 images. The carousel will show "unavailable" for missing slots — that's expected and won't break the layout.

## Mobile Notification with Image

Send a notification to your phone with the detection image when a new event occurs. Add this automation:

```yaml
automation:
  - alias: ZeroMOUSE detection alert
    trigger:
      - platform: state
        entity_id: sensor.zeromouse_last_event_time
    action:
      - variables:
          cat_name: "Cat"  # Change to your cat's name
          snapshot_filename: zeromouse_{{ now().strftime('%Y%m%d_%H%M%S') }}.jpg
      - action: image.snapshot
        target:
          entity_id: image.zeromouse_last_event
        data:
          filename: /config/www/zeromouse/{{ snapshot_filename }}
      - delay:
          milliseconds: 500
      - variables:
          classification: "{{ states('sensor.zeromouse_last_event_classification') }}"
      - action: notify.mobile_app_<your_phone>
        data:
          title: >
            {% if classification == 'prey' %}⚠️ Prey detected!
            {% elif classification == 'undecidable' %}⚠️ Uncertain detection
            {% else %}ZeroMOUSE{% endif %}
          message: >
            {% set messages = {
              'prey': cat_name ~ ' tried to bring in prey — entry was blocked!',
              'clean': cat_name ~ ' entered without prey.',
              'undecidable': 'Uncertain detection for ' ~ cat_name ~ ' — check the image.',
              'out': cat_name ~ ' went outside.',
              'late': 'Classification arrived too late — ' ~ cat_name ~ ' already through.',
              'test': 'Test event triggered.',
            } %}
            {{ messages.get(classification, classification ~ ' event detected') }}
          data:
            image: /local/zeromouse/{{ snapshot_filename }}
            push:
              interruption-level: "{{ 'critical' if classification in ['prey', 'undecidable'] else 'active' }}"
```

Replace `mobile_app_<your_phone>` with your device's notify service name.

## How it works

This integration communicates with the ZeroMOUSE cloud API (the same backend the official mobile app uses). It polls the device shadow state every 10 seconds and checks for new detection events every 60 seconds. No local network access to the device is required.

## Troubleshooting

**"Incorrect email or password"**
Make sure you're using the same credentials as the ZeroMOUSE mobile app.

**"No devices found"**
Your device must have recorded at least one detection event for auto-discovery to work. Open the ZeroMOUSE app and trigger a test event first.

**"Cannot connect to ZeroMOUSE cloud"**
Your Home Assistant instance needs internet access to reach AWS (eu-central-1 region).

**Session expired / re-authentication**
If your session expires (typically after several months), Home Assistant will show a notification. Click it to re-enter your credentials.

## License

This project is licensed under the [MIT License](LICENSE).

## Disclaimer

This integration is provided as-is, without warranty. It relies on undocumented cloud APIs that may change without notice. The author is not responsible for any issues arising from the use of this integration.

This project is not affiliated with, endorsed by, or connected to ZeroMOUSE or any of its subsidiaries or affiliates. All product names, logos, and brands are property of their respective owners.
