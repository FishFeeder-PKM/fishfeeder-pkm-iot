# FishFeeder IoT

Internet of Things (IoT) device codes to do the following:
1. Able to be remotely controlled to feed fish.
2. Able to send sensor data to the server every second.
3. Able to stream webcam video to peers.

## Installation Guide

1. Clone this repository.
2. Make sure to have Python3 binary installed on your machine.
3. Install requirements.
   ```
   python3 install.py
   ```
4. Independently start each services.
   ```
   python3 camera.py
   python3 sensor.py
   ```

## API Specification

### Feed Control
Control the IoT device.
- Topic: `${DEVICE_ID}/control`
- Payload:
```
{
    "type": "action",
    "action": "feed",
    "settings": {
        "duration": <integer>,
    },
}
```
  ~ "action":
    is required, is a command to be sent to the IoT device.
  
  ~ "settings.duration":
    is optional, is for how long should the FishFeeder machine do the feeding in second time format (interval), default value is `5` seconds.

- Response:
```
{
    "type": "status_update",
    "action": "feed",
    "state": "ongoing|stopped"
}
```

### Sensor Data
Get the sensor data
- Topic: `${DEVICE_ID}/sensor`
- Response:
```
{
    "ph": <float>,
    "tds": <float>,
    "do": <float>,
}
```
