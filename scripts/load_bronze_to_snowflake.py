import os
import json
import glob
import uuid
import snowflake.connector
from dotenv import load_dotenv

BRONZE_PATH = "data/bronze/airlabs/schedules"


load_dotenv()

SNOWFLAKE_CONFIG = {
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": "BRONZE",
    "role": os.getenv("SNOWFLAKE_ROLE"),
}


def get_snowflake_connection():
    """
    Create Snowflake connection.
    """

    return snowflake.connector.connect(**SNOWFLAKE_CONFIG)


def extract_metadata_from_file_path(file_path):
    """
    Extract airport and schedule type from the Bronze file path.

    Example path:
    data/bronze/airlabs/schedules/JFK/dep/JFK_dep_schedules_20260523_123000.json
    """

    normalized_path = file_path.replace("\\", "/")
    parts = normalized_path.split("/")

    source_airport_iata = parts[-3]
    schedule_type = parts[-2]
    source_file_name = parts[-1]

    return source_airport_iata, schedule_type, source_file_name


def load_json_file_to_snowflake(cursor, file_path):
    """
    Load one raw Bronze JSON file into Snowflake Bronze table.
    """

    source_airport_iata, schedule_type, source_file_name = extract_metadata_from_file_path(file_path)

    with open(file_path, "r") as file:
        raw_json = json.load(file)

    ingestion_id = str(uuid.uuid4())

    insert_sql = """
        INSERT INTO AIRLINE_Analytics_DB.BRONZE.RAW_AIRLABS_SCHEDULES
        (
            ingestion_id,
            raw_data,
            source_file_name,
            source_airport_iata,
            schedule_type,
            source_system,
            api_endpoint
        )
        SELECT
            %s,
            PARSE_JSON(%s),
            %s,
            %s,
            %s,
            %s,
            %s
    """

    cursor.execute(
        insert_sql,
        (
            ingestion_id,
            json.dumps(raw_json),
            source_file_name,
            source_airport_iata,
            schedule_type,
            "airlabs",
            "schedules"
        )
    )

    record_count = len(raw_json.get("response", []))

    print(
        f"Loaded: {source_file_name} | "
        f"Airport: {source_airport_iata} | "
        f"Type: {schedule_type} | "
        f"Records: {record_count}"
    )


def load_all_bronze_files():
    """
    Load all local Bronze JSON files into Snowflake Bronze table.
    """

    json_files = glob.glob(f"{BRONZE_PATH}/**/*.json", recursive=True)

    print(f"Bronze JSON files found: {len(json_files)}")

    if not json_files:
        print("No Bronze JSON files found. Please check your Bronze folder path.")
        return

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        for file_path in json_files:
            load_json_file_to_snowflake(cursor, file_path)

        conn.commit()
        print("All Bronze files loaded into Snowflake successfully.")

    except Exception as error:
        conn.rollback()
        print("Error while loading Bronze files into Snowflake.")
        print(error)
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    load_all_bronze_files()