import requests
from dotenv import load_dotenv
import json
import os
from datetime import datetime, timezone



load_dotenv()

API_KEY = os.getenv("AIRLABS_API_KEY")
BASE_URL = "https://airlabs.co/api/v9"

def load_config():
    """
    Load airport and schedule type configuration.
    """

    config_path = "config/airports.json"

    with open(config_path, "r") as file:
        config = json.load(file)

    airports = config.get("airports", [])
    schedule_types = config.get("schedule_types", ["dep", "arr"])

    if not airports:
        raise ValueError("No airports found in config/airports.json")

    return airports, schedule_types




def fetch_schedules(airport_iata, schedule_type):
    """
    Fetch raw flight schedule data from AirLabs API.

    schedule_type:
    dep = departures
    arr = arrivals
    """

    url = f"{BASE_URL}/schedules"

    if schedule_type == "dep":
        params = {
            "api_key": API_KEY,
            "dep_iata": airport_iata
        }
    elif schedule_type == "arr":
        params = {
            "api_key": API_KEY,
            "arr_iata": airport_iata
        }
    else:
        raise ValueError("schedule_type must be either 'dep' or 'arr'")

    response = requests.get(url, params=params, timeout=30)

    print("=" * 80)
    print(f"Airport: {airport_iata}")
    print(f"Schedule Type: {schedule_type}")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print("API Error Response:")
        print(response.text)
        response.raise_for_status()

    return response.json()


def save_raw_json(data, airport_iata, schedule_type):
    """
    Save raw API response exactly as received.
    This is the Bronze layer.
    """

    ingestion_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    folder_path = os.path.join(
        "data",
        "bronze",
        "airlabs",
        "schedules",
        airport_iata,
        schedule_type
    )

    os.makedirs(folder_path, exist_ok=True)

    file_name = f"{airport_iata}_{schedule_type}_schedules_{ingestion_timestamp}.json"
    file_path = os.path.join(folder_path, file_name)

    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

    record_count = len(data.get("response", []))

    print(f"Saved Bronze file: {file_path}")
    print(f"Record count: {record_count}")

    return file_path


def run_bronze_extraction():
    """
    Main function for Bronze extraction.
    Reads airports and schedule types from config file.
    """

    airports, schedule_types = load_config()

    print(f"Airports selected: {airports}")
    print(f"Schedule types selected: {schedule_types}")

    for airport in airports:
        for schedule_type in schedule_types:
            raw_data = fetch_schedules(airport, schedule_type)
            save_raw_json(raw_data, airport, schedule_type)

if __name__ == "__main__":
    run_bronze_extraction()