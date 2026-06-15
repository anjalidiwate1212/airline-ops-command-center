import os
import json
import glob
import pandas as pd
from datetime import datetime, timezone


BRONZE_PATH = "data/bronze/airlabs/schedules"
SILVER_PATH = "data/silver"


def read_bronze_files():
    """
    Read all Bronze JSON files from the AirLabs schedules folder.
    Extract the flight records from the 'response' array.
    """

    json_files = glob.glob(f"{BRONZE_PATH}/**/*.json", recursive=True)

    all_records = []

    print(f"Bronze files found: {len(json_files)}")

    for file_path in json_files:
        with open(file_path, "r") as file:
            raw_data = json.load(file)

        records = raw_data.get("response", [])

        # Extract airport and schedule type from folder path
        # Example path:
        # data/bronze/airlabs/schedules/JFK/dep/JFK_dep_schedules_20260523_123000.json
        path_parts = file_path.replace("\\", "/").split("/")
        airport_iata = path_parts[-3]
        schedule_type = path_parts[-2]

        for record in records:
            record["source_file"] = file_path
            record["source_airport_iata"] = airport_iata
            record["schedule_type"] = schedule_type

        all_records.extend(records)

    print(f"Total raw records extracted: {len(all_records)}")

    return all_records


def transform_to_silver(records):
    """
    Convert raw API records into a clean Silver dataframe.
    """

    if not records:
        print("No records found. Silver transformation stopped.")
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Columns we want to keep in Silver
    selected_columns = [
        "airline_iata",
        "airline_icao",
        "flight_iata",
        "flight_icao",
        "flight_number",

        "dep_iata",
        "dep_icao",
        "dep_terminal",
        "dep_gate",
        "dep_time",
        "dep_time_utc",
        "dep_estimated",
        "dep_estimated_utc",
        "dep_actual",
        "dep_actual_utc",

        "arr_iata",
        "arr_icao",
        "arr_terminal",
        "arr_gate",
        "arr_baggage",
        "arr_time",
        "arr_time_utc",
        "arr_estimated",
        "arr_estimated_utc",

        "cs_airline_iata",
        "cs_flight_number",
        "cs_flight_iata",

        "status",
        "duration",
        "delayed",
        "dep_delayed",
        "arr_delayed",
        "aircraft_icao",

        "source_airport_iata",
        "schedule_type",
        "source_file"
    ]

    # Keep only columns that actually exist in the API response
    existing_columns = [col for col in selected_columns if col in df.columns]
    df = df[existing_columns]

    # Convert time columns to datetime
    time_columns = [
        "dep_time",
        "dep_time_utc",
        "dep_estimated",
        "dep_estimated_utc",
        "dep_actual",
        "dep_actual_utc",
        "arr_time",
        "arr_time_utc",
        "arr_estimated",
        "arr_estimated_utc"
    ]

    for col in time_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert delay columns to numeric
    delay_columns = ["delayed", "dep_delayed", "arr_delayed", "duration"]

    for col in delay_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Create business-friendly flags
    df["is_codeshare"] = df["cs_flight_iata"].notna()

    df["marketing_flight_iata"] = df["flight_iata"]

    df["operating_flight_iata"] = df["cs_flight_iata"].fillna(df["flight_iata"])

    df["is_departure_record"] = df["schedule_type"].eq("dep")

    df["is_arrival_record"] = df["schedule_type"].eq("arr")

    df["is_cancelled"] = df["status"].fillna("").str.lower().str.contains("cancel")

    df["is_departure_delayed"] = df["dep_delayed"].fillna(0) > 15

    df["is_arrival_delayed"] = df["arr_delayed"].fillna(0) > 15

    df["silver_processed_at_utc"] = datetime.now(timezone.utc)

    # Remove exact duplicate rows if the same bronze file is processed again
    df = df.drop_duplicates()

    print(f"Silver records created: {len(df)}")

    return df


def save_silver_data(df):
    """
    Save clean Silver data locally as CSV.
    """

    if df.empty:
        print("No Silver data to save.")
        return

    os.makedirs(SILVER_PATH, exist_ok=True)

    output_file = os.path.join(SILVER_PATH, "flight_schedules_clean.csv")

    df.to_csv(output_file, index=False)

    print(f"Silver file saved: {output_file}")


def run_silver_transformation():
    records = read_bronze_files()
    silver_df = transform_to_silver(records)
    save_silver_data(silver_df)


if __name__ == "__main__":
    run_silver_transformation()