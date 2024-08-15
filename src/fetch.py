import adafruit_requests
import os

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
if SUPABASE_URL is "":
    raise ValueError("SUPABASE_URL environment variable is not set")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_dashboard_data(requests: adafruit_requests.Session):
    """Fetch the latest data from the API."""
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/dashboard-snapshots?select=data&order=id.desc&limit=1&testing=neq.True",
        headers={"apikey": SUPABASE_KEY},
    )

    if response.status_code != 200:
        raise ValueError(f"Failed to fetch data: {response.status_code}")

    return response.json()[0]["data"]
