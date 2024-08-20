import os
import ssl
import time

import adafruit_requests
import board
import busio
import socketpool
import wifi
from adafruit_max1704x import MAX17048
from adafruit_scd4x import SCD4X

from alerts import CO2Alert
from notify import TwilioNotifier
from display import Dashboard
import fetch

ELECTRICITYMAPS_ZONE: str = os.getenv("ELECTRICITYMAPS_ZONE", "")

# raise an error if the environment variable is not set
if ELECTRICITYMAPS_ZONE == "":
    raise ValueError("ELECTRICITYMAPS_ZONE environment variable is not set")

LOW_POWER_MODE = True

TIER1_PRICE = 1030
TIER2_PRICE = 1250
TIER1_LIMIT = 600

# This controls how often your device sends data to the database
INTERVAL_S = 60


# Prepare to use the internet 💫
def initialize_wifi_connection():
    # This is inside a function so that we can call it later if we need to reestablish
    # the connection.
    wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))


def initialize_sensors():
    """Initialize connections to each possible sensor, if connected"""
    i2c = busio.I2C(board.SCL, board.SDA)

    try:
        co2_sensor = SCD4X(i2c)
        print("Found SCD4X CO2, temp and humidity sensor")
        if LOW_POWER_MODE:
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
        temp = co2_sensor.temperature

        all_sensor_data.update(
            {
                "co2_ppm": co2_sensor.CO2,
                "temperature_c": temp,
                "humidity_relative": co2_sensor.relative_humidity,
            }
        )

    return all_sensor_data


display = board.DISPLAY
display.brightness = 0.1

dashboard = Dashboard(display, TIER1_PRICE, TIER2_PRICE, TIER1_LIMIT)

initialize_wifi_connection()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

(
    co2_sensor,
    battery_sensor,
) = initialize_sensors()

time.sleep(5)

co2_alert_handler: CO2Alert = CO2Alert(
    notifier=TwilioNotifier(requests),
    co2_unsafe_over=1000,
    co2_safe_under=800,
)

while True:
    data = collect_data(co2_sensor, battery_sensor)
    print(data)
    co2_ppm = data.get("co2_ppm", 0)
    co2_alert_handler.alert_maybe(co2_ppm)

    dashboard_data = fetch.get_dashboard_data(requests, ELECTRICITYMAPS_ZONE)
    dashboard.update(
        carbon_intensity_history=dashboard_data["carbon_intensity_history"],
        power_consumption_history=dashboard_data["power_consumption_history"],
        energy_usage_kwh=dashboard_data["philip_utility_data"]["energy_usage_kwh"],
        tier_limit=dashboard_data["philip_utility_data"]["tier_limit"],
        tier1_price=dashboard_data["philip_utility_data"]["tier1_price"] * 1000,
        tier2_price=dashboard_data["philip_utility_data"]["tier2_price"] * 1000,
    )

    time.sleep(INTERVAL_S)
