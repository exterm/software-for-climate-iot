import adafruit_requests
import os
from adafruit_datetime import datetime, timedelta

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
if SUPABASE_URL == "":
    raise ValueError("SUPABASE_URL environment variable is not set")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_dashboard_data(requests: adafruit_requests.Session, zone: str):
    """
    Fetch the latest data from the API directly from raw data.
    Compute display values from raw data.
    """

    print("Fetching dashboard data...")

    # don't trust the system clock. Get the current time from the internet
    response = requests.get("http://worldtimeapi.org/api/timezone/UTC")

    if response.status_code != 200:
        raise ValueError(f"Failed to fetch time data: {response.status_code}. Error: {response.text}")

    time_data = response.json()
    now_utc: datetime = datetime.fromtimestamp(time_data["unixtime"])

    # Calculate the start and end dates for the last week
    start_date = now_utc - timedelta(days=2)

    # Get all rows within the last week for the specified zone
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/electricitymaps-hourly?" +
            "select=carbon_intensity_raw,power_breakdown_raw&order=created_at.asc" +
            f"&created_at=gte.{start_date}&zone=eq.{zone}&testing=neq.True",
        headers={"apikey": SUPABASE_KEY},
    )

    if response.status_code != 200:
        raise ValueError(f"Failed to fetch electricitymaps data: {response.status_code}. Error: {response.json()}")

    data = response.json()

    # Filter out duplicate rows for each hour and build the 7-day history
    carbon_intensity_history = []
    power_consumption_history = []

    for row in data:
        carbon_intensity_history.append(row["carbon_intensity_raw"]["history"][-1])
        power_consumption_history.append(row["power_breakdown_raw"]["history"][-1])

    # add remaining 23 hours of the latest row
    latest_row = data[-1]

    for i in reversed(range(23)):
        carbon_intensity_history.append(latest_row["carbon_intensity_raw"]["history"][i])
        power_consumption_history.append(latest_row["power_breakdown_raw"]["history"][i])

    print(len(carbon_intensity_history))
    print([row["datetime"] for row in carbon_intensity_history])

    # Extract numeric values (carbonIntensity, powerConsumptionTotal) from the raw data
    carbon_intensity_history = [datapoint["carbonIntensity"] for datapoint in carbon_intensity_history]
    power_consumption_history = [datapoint["powerConsumptionTotal"] for datapoint in power_consumption_history]

    # utility data for Philip
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/private-utility-datapoints?" +
            "select=data&order=created_at.desc&limit=1" +
            "&testing=neq.True&household=eq.Philip%27s%20Place",
        headers={"apikey": SUPABASE_KEY},
    )

    if response.status_code != 200:
        raise ValueError(f"Failed to fetch private utility data: {response.status_code}. Error: {response.json()}")

    data = response.json()[0]

    energy_usage_kwh = data["data"]["total_usage"]
    tier_limit = data["data"]["tiered_pricing_data"]["tierThreshold"]
    tier1_price = data["data"]["tiered_pricing_data"]["tier1Rate"]
    tier2_price = data["data"]["tiered_pricing_data"]["tier2Rate"]

    return {
        "carbon_intensity_history": carbon_intensity_history,
        "power_consumption_history": power_consumption_history,
        "philip_utility_data": {
            "energy_usage_kwh": energy_usage_kwh,
            "tier_limit": tier_limit,
            "tier1_price": tier1_price,
            "tier2_price": tier2_price,
        },
    }
