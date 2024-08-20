import adafruit_requests
import os

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
if SUPABASE_URL == "":
    raise ValueError("SUPABASE_URL environment variable is not set")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_dashboard_data(requests: adafruit_requests.Session, zone: str):
    """
    Fetch the latest data from the API directly from raw data.
    Compute display values from raw data.
    """

    # get the latest row in the electricitymaps-hourly table for each zone (where testing is false)
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/electricitymaps-hourly?" +
            "select=carbon_intensity_raw,power_breakdown_raw&order=created_at.desc&limit=1" +
            f"&testing=neq.True&zone=eq.{zone}",
        headers={"apikey": SUPABASE_KEY},
    )

    if response.status_code != 200:
        raise ValueError(f"Failed to fetch electricitymaps data: {response.status_code}. Error: {response.json()}")

    data = response.json()[0]

    carbon_intensity_history: list[int] = [row["carbonIntensity"] for row in data["carbon_intensity_raw"]["history"]]

    power_consumption_history: list[int] = [row["powerConsumptionTotal"] for row in data["power_breakdown_raw"]["history"]]

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
