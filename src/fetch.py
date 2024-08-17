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
        raise ValueError(f"Failed to fetch data: {response.status_code}. Error: {response.json()}")

    data = response.json()[0]

    latest_carbon_intensity = data["carbon_intensity_raw"]["history"][0]["carbonIntensity"]
    average_carbon_intensity = sum(
        [x["carbonIntensity"] for x in data["carbon_intensity_raw"]["history"]]
    ) / len(data["carbon_intensity_raw"]["history"])

    latest_power_consumption = data["power_breakdown_raw"]["history"][0]["powerConsumptionTotal"]
    average_power_consumption = sum(
        [x["powerConsumptionTotal"] for x in data["power_breakdown_raw"]["history"]]
    ) / len(data["power_breakdown_raw"]["history"])

    return {
        "latest_carbon_intensity": latest_carbon_intensity,
        "average_carbon_intensity": average_carbon_intensity,
        "latest_power_consumption": latest_power_consumption,
        "average_power_consumption": average_power_consumption,
    }

