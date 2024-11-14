import time
import paho.mqtt.client as mqtt
import random
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz

# Load environment variables from the .env file
load_dotenv(f"{os.path.dirname(os.path.abspath(__file__))}/../.env")

# MQTT Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT"))
MQTT_QOS = int(os.getenv("MQTT_QOS"))
DEVICE_ID = os.getenv("DEVICE_ID")

# Define topics
SENSOR_TOPIC = f"{DEVICE_ID}/sensor"
STATUS_TOPIC = f"{DEVICE_ID}/status"
CONTROL_TOPIC = f"{DEVICE_ID}/control"

# Define the timezone UTC+7 (Bangkok Time)
tz = pytz.timezone(os.getenv("CONFIG_TIMEZONE"))

# Convert time strings to datetime objects in UTC+7
def parse_time(time_str):
    return datetime.strptime(time_str, "%H:%M").replace(tzinfo=tz)

# Feeder configuration (default immutable values)
config_immutable = {
    is_auto_feed: True, # automatically feeds or not
    auto_feed_start: parse_time("08:00"), # time UTC+7, when the feedings can occur
    auto_feed_end: parse_time("20:00"), # time UTC+7, when the feedings must stop
    auto_feed_interval: 4, # hours
    feed_duration: 5, # seconds to open feeder valve
}

# Copy the immutable config into mutable ones (on runtiem)
config = config_immutable.copy()

# FETCH CONFIG FROM REST API @ /api/v1/devices/{DEVICE_ID}/configs

# Callback for successful connection
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    # Subscribe to control topics (feed control)
    client.subscribe(CONTROL_TOPIC)
    print(f"Subscribed to control topics: {CONTROL_TOPIC}")

    client.publish(STATUS_TOPIC, json.dumps({ "is_online": True }), qos=1)
    print(f"Sent connectivity status to: {STATUS_TOPIC}")

# Callback for when the client is disconnected
def on_disconnect(client, userdata, rc):
    print(f"Disconnected from broker with result code {rc}")
    if rc != 0:  # If the disconnection was not initiated by the client, try to reconnect
        print("Attempting to reconnect...")
        client.reconnect()

# Callback for when a message is received on a subscribed topic
def on_message(client, userdata, msg):
    # Handle control commands
    if msg.topic == CONTROL_TOPIC:
        data = json.loads(msg.payload)
        message_type = data.get("type")
        if message_type == "action":
            action = data.get("action")
            settings = data.get("settings", None)
            if action == "feed" and config.is_auto_feed == False:
                duration = settings["duration"] if settings is not None else config.feed_duration
                manual_feed(duration)
            
            if action == "config":
                config.is_auto_feed = settings["is_auto_feed"] if settings is not None else config.is_auto_feed

                if is_auto_feed:
                    config.auto_feed_start = settings["is_auto_feed"] if settings is not None else config.auto_feed_start
                    config.auto_feed_end = settings["is_auto_feed"] if settings is not None else config.auto_feed_end
                    config.auto_feed_interval = settings["is_auto_feed"] if settings is not None else config.auto_feed_interval

# Example function to simulate feeding action
def manual_feed(duration):
    print(f"Feeding for {duration} seconds.")
    client.publish(CONTROL_TOPIC, json.dumps({
        "type": "status_update",
        "action": "feed",
        "state": "ongoing",
    }), qos=MQTT_QOS)

    #######################################
    """
    CHANGE THIS CODE TO ACTUAL FEEDING CODE
    """
    time.sleep(duration)
    #######################################

    # Feeding finished
    print("Feeding stopped.")
    client.publish(CONTROL_TOPIC, json.dumps({
        "type": "status_update",
        "action": "feed",
        "state": "stopped",
    }), qos=MQTT_QOS)

def auto_feed():
    # Get the current time in UTC+7
    current_time = datetime.now(tz)



# Create a new MQTT client and specify the callback API version
client = mqtt.Client(DEVICE_ID)

# Client configs
client.keep_alive_interval = 30  # Set to 30 seconds or less
client.reconnect_delay_set(min_delay=1, max_delay=120)  # Reconnect after 1s, up to 2 minutes max
client.will_set(STATUS_TOPIC, json.dumps({ "is_online": False }), qos=1, retain=True)
# client.tls_set(certfile="/path/to/cert.pem", keyfile="/path/to/key.pem", tls_version=ssl.PROTOCOL_TLS)

# Set up callback functions
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

# Connect to the broker
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Start the MQTT client loop in a separate thread
client.loop_start()

# Simulate sending sensor data to different topics every second
try:
    auto_feed()

    while True:
        #################################
        """
        SENSOR DATA RETRIEVAL LOGIC HERE
        """
        #################################
        sensor_data = {
            "ph": round(random.uniform(20.0, 30.0), 2),
            "tds": round(random.uniform(30.0, 60.0), 2),
            "do": round(random.uniform(30.0, 60.0), 2),
        }

        # Publish data to different topics
        client.publish(SENSOR_TOPIC, json.dumps(sensor_data), qos=MQTT_QOS)
        
        print(f"Published to {SENSOR_TOPIC}: {sensor_data}")

        # Auto feed


        # Wait for 1 second before sending the next data
        time.sleep(1)

except KeyboardInterrupt:
    print("Exiting program...")
    client.loop_stop()
    client.disconnect()
