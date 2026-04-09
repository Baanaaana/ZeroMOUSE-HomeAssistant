# ZeroMOUSE Firmware Analysis (v0.16.27)

## AWS IoT Endpoint
```
a1lrk6d93bvma9-ats.iot.eu-central-1.amazonaws.com
```
Region: eu-central-1

## MQTT Topic Structure
Standard AWS IoT Shadow (no custom `/zm/` topics found):
- `$aws/things/{thingName}/shadow/update` — device publishes reported state
- `$aws/things/{thingName}/shadow/update/accepted`
- `$aws/things/{thingName}/shadow/update/delta` — desired vs reported diff
- `$aws/things/{thingName}/shadow/get` / `/accepted` / `/rejected`
- `$aws/things/{thingName}/shadow/delete` / `/accepted` / `/rejected`

Fleet provisioning:
- `$aws/certificates/create/json` / `/accepted` / `/rejected`
- `$aws/provisioning-templates/{templateName}/provision/json` / `/accepted` / `/rejected`

OTA via AWS IoT Jobs:
- Standard `$aws/things/{thingName}/jobs/...` topics

Dynamic image publish topic stored in NVS as `pubImageTopic`.

## Shadow Document Structure
```json
{
  "state": {
    "reported": {
      "system": {
        "swVersion": "",
        "verMajor": 0, "verMinor": 0, "verRevision": 0,
        "verHardware": "",
        "bootCount": 0,
        "pirTriggerCount": 0,
        "airThrsholdCount": 0,
        "eventCount": 0,
        "ownerID": "",
        "identityID": "",
        "deviceID": "",
        "logEnabled": false,
        "uploadEmpty": false,
        "undecidableMode": 0,
        "finaleIntervalMaxCount": 0,
        "finaleIntervalDelta": 0,
        "metricLastResetReason": "",
        "metricMQTTErrorCount": 0,
        "metricWifiConnectCount": 0,
        "metricWifiRSSI": 0
      },
      "camera": {
        "cameraStatus": 0,
        "brightness": 0,
        "exposureCtrl": 0,
        "gainCtrl": 0,
        "gainCtrlMax": 0,
        "whiteBalance": 0,
        "hMirror": 0,
        "vFlip": 0,
        "autoExpLevel": 0,
        "autoGainCtrl": 0,
        "autoGainCtrlMin": 0,
        "autoGainCtrlMax": 0,
        "autoGainStbl": 0,
        "autoGainStblMin": 0,
        "autoGainStblMax": 0,
        "gainCeiling": 0,
        "camShotsBeforeT0": 0
      },
      "proximity": {
        "irSensorStatus": 0,
        "irFreeValue": 0,
        "irFreeValueRaw": 0,
        "irRangeIgnoreEvent": 0,
        "irPreyEventTime": 0,
        "irMedianCount": 0,
        "irAmbient": 0,
        "irSlopeThreshValue": 0,
        "irMotionThrsh": 0,
        "irPresenceThrsh": 0,
        "blockEnabled": false,
        "blockState": 0,
        "blockCount": 0,
        "unblockCount": 0,
        "unblockRstCount": 0,
        "responseTimeout": 0,
        "lastRefEventMaxCount": 0,
        "lastRefEventMaxTimeSec": 0
      },
      "rfid": {},
      "pubImageTopic": ""
    },
    "desired": {}
  }
}
```

## Key Behavioral Notes

### blockState bitmask
- `blockState & 1` = flap is BLOCKED (locked)
- `!(blockState & 1)` = flap is UNBLOCKED (open)

### undecidableMode
- `0` = default (unknown behavior)
- `1` = treat undecidable classification as CLEAN (allow through)
- `2` = treat undecidable classification as BLOCKED (deny entry)

### Event publish subsystems
- `IOT_PUB_DEVICE` — periodic device telemetry
- `IOT_PUB_EVENT` — detection events (system + camera + proximity data)
- `IOT_PUB_IMAGES` — camera image uploads to dynamic `pubImageTopic`

### Event JSON fields
- `eventID`, `eventTime`, `cleanEventTime`
- `finaleFreePercent`, `finaleMeanDelta`
- `prevEventLogs`, `images`, `imageData`, `imageIndex`
- `respDelayCSecs` (response delay in centiseconds)
