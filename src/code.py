import json
import os
import ssl
import time
import traceback

import adafruit_requests
import board
import busio
import microcontroller
import socketpool
import wifi
from adafruit_max1704x import MAX17048
from adafruit_scd4x import SCD4X

import notify

DEVICE_ID = os.getenv("DEVICE_ID")
SUPABASE_POST_URL = os.getenv("SUPABASE_POST_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LOCATION = os.getenv("LOCATION")

LOW_POWER_MODE = True
LOW_POWER_TEMP_OFFSET = 2.5

# This controls how often your device sends data to the database
INTERVAL_S = 60

# Prepare to use the internet 💫
def initialize_wifi_connection():
    # This is inside a function so that we can call it later if we need to reestablish
    # the connection.
    wifi.radio.connect(
        os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
    )

def initialize_sensors():
    """Initialize connections to each possible sensor, if connected"""
    i2c = busio.I2C(board.SCL, board.SDA)

    try:
        co2_sensor = SCD4X(i2c)
        print("Found SCD4X CO2, temp and humidity sensor")
        if LOW_POWER_MODE:
            co2_sensor.temperature_offset = LOW_POWER_TEMP_OFFSET
            co2_sensor.start_low_periodic_measurement()
        else:
            co2_sensor.start_periodic_measurement()
    except Exception:
        print("No SCD4X sensor found")
        co2_sensor = None

    try:
        battery_sensor = MAX17048(i2c)
        print("Found battery sensor")
    except Exception:
        print("No battery sensor found")
        battery_sensor = None

    print()

    # return air_quality_sensor, co2_sensor, temperature_sensor, battery_sensor
    return co2_sensor, battery_sensor


def post_to_db(sensor_data: dict):
    """Store sensor data in our supabase DB along with appropriate metadata"""
    if not DEVICE_ID:
        raise Exception("Please set a unique device id!")

    # Prepare the database row, augmenting the sensor data with metadata
    db_row = {
        "device_id": DEVICE_ID,
        "content": dict(
            location=LOCATION,
            **sensor_data
        ),
    }
    # print(db_row)
    print("Report:")
    print("Battery percentage:", round(db_row["content"]["battery_pct"], 2), "%")
    if db_row["content"].get("temperature_c"):
        print("Temperature:", round(db_row["content"]["temperature_c"], 2), "°C")
        print("Humidity:", round(db_row["content"]["humidity_relative"], 2), "%")
        print("CO2:", round(db_row["content"]["co2_ppm"], 2), "ppm")

    # print("Posting to DB at", fetch_current_time())
    print("Posting to DB")
    try:
        response = requests.post(
            url=SUPABASE_POST_URL,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            data=json.dumps(db_row),
        )
    except socketpool.SocketPool.gaierror as e:
        print(f"ConnectionError: {e}. Restarting networking.")
        initialize_wifi_connection()
        # Attempt to store some diagnostic data about this error
        sensor_data.update(
            {"network_reset": True, "network_stacktrace": traceback.format_exception(e)}
        )
        print("Recursively retrying post with saved stacktrace.")
        response = post_to_db(sensor_data)

    # PostgREST only sends response to a POST when something is wrong
    error_details = response.content
    if error_details:
        print("Received response error code", error_details)
        print(response.headers)
        raise Exception(error_details)
    else:
        print("Post complete")

    print()

    return response

def collect_data(co2_sensor, battery_sensor):
    """Get the latest data from the sensors, display it, and record it in the cloud."""
    # Python3 kwarg-style dict concatenation syntax doesn't seem to work in CircuitPython,
    # so we have to use mutation and update the dict as we go along
    all_sensor_data = {}

    if battery_sensor:
        all_sensor_data.update(
            {
                "battery_v": battery_sensor.cell_voltage,
                "battery_pct": battery_sensor.cell_percent,
            }
        )

    if co2_sensor and co2_sensor.data_ready:
        all_sensor_data.update(
            {
                "co2_ppm": co2_sensor.CO2,
                "temperature_c": co2_sensor.temperature,
                "humidity_relative": co2_sensor.relative_humidity,
            }
        )

    return all_sensor_data

display = board.DISPLAY
display.brightness = 0.1

initialize_wifi_connection()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

(
    co2_sensor,
    battery_sensor,
) = initialize_sensors()

time.sleep(5)

CO2_UNSAFE_OVER = 1000
CO2_SAFE_UNDER = 800
print(f"CO2 thresholds set to {CO2_UNSAFE_OVER} ppm (unsafe) and {CO2_SAFE_UNDER} ppm (safe).")
notifier = notify.TwilioNotifier(requests)

co2_alert_active = False

while True:
    try:
        data = collect_data(co2_sensor, battery_sensor)
        co2_ppm = data.get("co2_ppm", 0)
        if not co2_alert_active and co2_ppm > CO2_UNSAFE_OVER:
            notifier.send_alert(f"Reached unsafe CO2 levels ({co2_ppm}).")
            co2_alert_active = True
        elif co2_alert_active and co2_ppm < CO2_SAFE_UNDER:
            notifier.send_alert("CO2 levels returned to normal.")
            co2_alert_active = False
        post_to_db(data)
    except (RuntimeError, OSError) as e:
        # Sometimes this is invalid PM2.5 checksum or timeout
        print(f"{type(e)}: {e}")
        if str(e) == "pystack exhausted":
            # This happens when our recursive retry logic fails.
            print("Unable to recover from an error. Rebooting in 10s.")
            time.sleep(10)
            microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
            microcontroller.reset()

    time.sleep(INTERVAL_S)
