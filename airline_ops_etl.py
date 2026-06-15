
import requests
import json

API_KEY = "7e805043-4d51-44c7-a3d9-fb95897de003"
BASE_URL = "https://airlabs.co/api/v9"


def test_ping():
    url = f"{BASE_URL}/ping"

    params = {
        "api_key": API_KEY
    }

    response = requests.get(url, params=params, timeout=30)

    print("PING STATUS CODE:", response.status_code)
    print(json.dumps(response.json(), indent=4))


def test_jfk_departures():
    url = f"{BASE_URL}/schedules"

    params = {
        "api_key": API_KEY,
        "dep_iata": "JFK"
    }

    response = requests.get(url, params=params, timeout=30)

    print("SCHEDULE STATUS CODE:", response.status_code)

    data = response.json()

    print(json.dumps(data, indent=4))

    records = data.get("response", [])
    print("Number of records:", len(records))

    if records:
        print("First flight record:")
        print(json.dumps(records[0], indent=4))


test_ping()
test_jfk_departures()