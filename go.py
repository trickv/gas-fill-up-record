import os
import requests
from datetime import datetime, timedelta

# ==== CONFIG ====
IMMICH_URL = "https://immich.home.v9n.us"
API_KEY = os.getenv("API_KEY")
DAYS_BACK = 14
MATCH_WINDOW_MINUTES = 30

if not API_KEY:
    raise EnvironmentError("API_KEY environment variable not set")

HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json"
}


# ==== SMART CLIP SEARCH ====
def smart_search_clip(term, days_back):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)

    payload = {
        "query": term,
        "takenAfter": start_date.isoformat() + "Z",
        "takenBefore": end_date.isoformat() + "Z",
        "size": 100,
        "withExif": True
    }

    r = requests.post(f"{IMMICH_URL}/api/search/smart", json=payload, headers=HEADERS)
    r.raise_for_status()
    print(r.json())
    return r.json()


# ==== TIMESTAMP PARSER ====
def parse_asset_time(asset):
    try:
        return datetime.fromisoformat(asset["exifInfo"]["dateTimeOriginal"].replace("Z", "+00:00"))
    except Exception:
        return None


# ==== FIND CLOSEST PUMP MATCH ====
def find_closest_pump(odo_time, pump_assets, max_diff_minutes):
    closest = None
    min_diff = timedelta(minutes=max_diff_minutes)

    for pump in pump_assets:
        pump_time = parse_asset_time(pump)
        if not pump_time:
            continue

        diff = abs(pump_time - odo_time)
        if diff <= min_diff:
            closest = pump
            min_diff = diff

    return closest


# ==== MAIN ====
if __name__ == "__main__":
    print("🔍 Searching for odometer images...")
    odometer_assets = smart_search_clip("odometer", DAYS_BACK)
    print(f"🧭 Found {len(odometer_assets)} odometer images")

    print("🔍 Searching for gas pump images...")
    pump_assets = smart_search_clip("gas pump", DAYS_BACK)
    print(f"⛽ Found {len(pump_assets)} gas pump images")

    print("\n📊 Matching odometer with gas pump images:\n")

    for odo in odometer_assets:
        print(f"examining: {IMMICH_URL}/api/asset/thumbnail/{odo}")
        odo_time = parse_asset_time(odo)
        if not odo_time:
            continue

        match = find_closest_pump(odo_time, pump_assets, MATCH_WINDOW_MINUTES)
        if not match:
            continue

        match_time = parse_asset_time(match)

        print("🪪 Matched Fill-Up:")
        print(f"📷 Odometer ID: {odo['id']}")
        print(f"    📅 Time: {odo_time}")
        print(f"    🖼️ Thumbnail: {IMMICH_URL}/api/asset/thumbnail/{odo['id']}")
        print(f"📷 Pump ID:     {match['id']}")
        print(f"    📅 Time: {match_time}")
        print(f"    🖼️ Thumbnail: {IMMICH_URL}/api/asset/thumbnail/{match['id']}")
        print("-" * 40)
