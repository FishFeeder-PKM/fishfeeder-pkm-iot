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
    "command": "feed",
    "duration": <integer>
}
```
  ~ "command":
    is required, is a command to be sent to the IoT device.
  
  ~ "duration":
    is optional, is for how long should the FishFeeder machine do the feeding in second time format (interval), default value is `10`.

Response:
```
{
    "command": "feed",
    "status": "ongoing|stopped"
}
```

### Sensor Data
Get the sensor data
```
Topic: fishfeeder/${DEVICE_ID}/sensor/data
```
- Topic: `fishfeeder/${DEVICE_ID}/sensor/data`
- Payload:
```
{
    "ph": <float>,
    "tds": <float>
}
```

Response:
```
{
    "ph": "<float>",
    "tds": "<float>"
}
```
