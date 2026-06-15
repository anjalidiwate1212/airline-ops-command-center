import os
import pandas as pd
from datetime import datetime, timezone


SILVER_FILE = "data/silver/flight_schedules_clean.csv"
GOLD_PATH = "data/gold"


def load_silver_data():
    """
    Load the clean Silver flight schedule data.
    """

    if not os.path.exists(SILVER_FILE):
        raise FileNotFoundError(f"Silver file not found: {SILVER_FILE}")

    df = pd.read_csv(SILVER_FILE)

    print(f"Silver records loaded: {len(df)}")

    return df


def prepare_gold_base(df):
    """
    Prepare common fields needed for Gold aggregations.
    """

    datetime_columns = [
        "dep_time",
        "arr_time",
        "dep_actual",
        "arr_actual",
        "dep_estimated",
        "arr_estimated"
    ]

    for col in datetime_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    numeric_columns = [
        "duration",
        "delayed",
        "dep_delayed",
        "arr_delayed"
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    boolean_columns = [
        "is_departure_delayed",
        "is_arrival_delayed",
        "is_cancelled",
        "is_codeshare",
        "is_departure_record",
        "is_arrival_record"
    ]

    for col in boolean_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().map({
                "true": True,
                "false": False,
                "1": True,
                "0": False
            }).fillna(False)

    # Choose operation timestamp based on record type
    df["operation_datetime"] = df["dep_time"]

    if "schedule_type" in df.columns:
        df.loc[df["schedule_type"].str.upper() == "ARR", "operation_datetime"] = df["arr_time"]

    df["operation_date"] = df["operation_datetime"].dt.date
    df["operation_hour"] = df["operation_datetime"].dt.hour

    df["route"] = df["dep_iata"].astype(str) + "-" + df["arr_iata"].astype(str)

    df["gold_processed_at_utc"] = datetime.now(timezone.utc)

    return df


def create_daily_airport_operations(df):
    """
    Create airport-level daily operations KPI table.
    """

    grouped = df.groupby(
        ["source_airport_iata", "operation_date"],
        dropna=False
    ).agg(
        total_flights=("flight_iata", "count"),
        departure_flights=("is_departure_record", "sum"),
        arrival_flights=("is_arrival_record", "sum"),
        delayed_departures=("is_departure_delayed", "sum"),
        delayed_arrivals=("is_arrival_delayed", "sum"),
        cancelled_flights=("is_cancelled", "sum"),
        avg_departure_delay_minutes=("dep_delayed", "mean"),
        avg_arrival_delay_minutes=("arr_delayed", "mean"),
        unique_airlines=("airline_iata", "nunique"),
        unique_routes=("route", "nunique")
    ).reset_index()

    grouped["on_time_departure_percentage"] = (
        (grouped["departure_flights"] - grouped["delayed_departures"])
        / grouped["departure_flights"].replace(0, float("nan"))
        * 100
    ).round(2)

    grouped["avg_departure_delay_minutes"] = grouped["avg_departure_delay_minutes"].round(2).fillna(0)
    grouped["avg_arrival_delay_minutes"] = grouped["avg_arrival_delay_minutes"].round(2).fillna(0)

    return grouped


def create_airline_performance(df):
    """
    Create airline-level KPI table.
    """

    grouped = df.groupby(
        ["airline_iata"],
        dropna=False
    ).agg(
        total_flights=("flight_iata", "count"),
        departure_flights=("is_departure_record", "sum"),
        arrival_flights=("is_arrival_record", "sum"),
        delayed_departures=("is_departure_delayed", "sum"),
        delayed_arrivals=("is_arrival_delayed", "sum"),
        cancelled_flights=("is_cancelled", "sum"),
        avg_departure_delay_minutes=("dep_delayed", "mean"),
        avg_arrival_delay_minutes=("arr_delayed", "mean"),
        routes_served=("route", "nunique"),
        airports_served=("source_airport_iata", "nunique")
    ).reset_index()

    grouped["departure_delay_rate_percentage"] = (
        grouped["delayed_departures"]
        / grouped["departure_flights"].replace(0, float("nan"))
        * 100
    ).round(2)

    grouped["arrival_delay_rate_percentage"] = (
        grouped["delayed_arrivals"]
        / grouped["arrival_flights"].replace(0, float("nan"))
        * 100
    ).round(2)

    grouped["avg_departure_delay_minutes"] = grouped["avg_departure_delay_minutes"].round(2).fillna(0)
    grouped["avg_arrival_delay_minutes"] = grouped["avg_arrival_delay_minutes"].round(2).fillna(0)

    return grouped


def create_route_performance(df):
    """
    Create route-level KPI table.
    """

    grouped = df.groupby(
        ["dep_iata", "arr_iata", "route"],
        dropna=False
    ).agg(
        total_flights=("flight_iata", "count"),
        unique_airlines=("airline_iata", "nunique"),
        delayed_departures=("is_departure_delayed", "sum"),
        delayed_arrivals=("is_arrival_delayed", "sum"),
        avg_departure_delay_minutes=("dep_delayed", "mean"),
        avg_arrival_delay_minutes=("arr_delayed", "mean"),
        cancelled_flights=("is_cancelled", "sum")
    ).reset_index()

    grouped["departure_delay_rate_percentage"] = (
        grouped["delayed_departures"]
        / grouped["total_flights"].replace(0, float("nan"))
        * 100
    ).round(2).fillna(0)

    grouped["avg_departure_delay_minutes"] = grouped["avg_departure_delay_minutes"].round(2).fillna(0)
    grouped["avg_arrival_delay_minutes"] = grouped["avg_arrival_delay_minutes"].round(2).fillna(0)

    return grouped


def create_hourly_flight_volume(df):
    """
    Create hourly airport operations table.
    """

    grouped = df.groupby(
        ["source_airport_iata", "operation_date", "operation_hour"],
        dropna=False
    ).agg(
        total_flights=("flight_iata", "count"),
        departure_flights=("is_departure_record", "sum"),
        arrival_flights=("is_arrival_record", "sum"),
        delayed_departures=("is_departure_delayed", "sum"),
        delayed_arrivals=("is_arrival_delayed", "sum"),
        avg_departure_delay_minutes=("dep_delayed", "mean")
    ).reset_index()

    grouped["avg_departure_delay_minutes"] = grouped["avg_departure_delay_minutes"].round(2).fillna(0)

    return grouped


def create_gate_terminal_utilization(df):
    """
    Create terminal/gate utilization table for departures.
    """

    dep_df = df[df["is_departure_record"] == True].copy()

    grouped = dep_df.groupby(
        ["source_airport_iata", "dep_terminal", "dep_gate"],
        dropna=False
    ).agg(
        total_departures=("flight_iata", "count"),
        delayed_departures=("is_departure_delayed", "sum"),
        avg_departure_delay_minutes=("dep_delayed", "mean"),
        unique_airlines=("airline_iata", "nunique"),
        unique_routes=("route", "nunique")
    ).reset_index()

    grouped["avg_departure_delay_minutes"] = grouped["avg_departure_delay_minutes"].round(2).fillna(0)

    grouped = grouped.sort_values(
        by=["source_airport_iata", "total_departures"],
        ascending=[True, False]
    )

    return grouped


def save_gold_table(df, table_name):
    """
    Save Gold table as CSV.
    """

    os.makedirs(GOLD_PATH, exist_ok=True)

    output_file = os.path.join(GOLD_PATH, f"{table_name}.csv")

    df.to_csv(output_file, index=False)

    print(f"Gold table saved: {output_file} | Records: {len(df)}")


def run_gold_creation():
    silver_df = load_silver_data()
    gold_base_df = prepare_gold_base(silver_df)

    daily_airport_operations = create_daily_airport_operations(gold_base_df)
    airline_performance = create_airline_performance(gold_base_df)
    route_performance = create_route_performance(gold_base_df)
    hourly_flight_volume = create_hourly_flight_volume(gold_base_df)
    gate_terminal_utilization = create_gate_terminal_utilization(gold_base_df)

    save_gold_table(daily_airport_operations, "daily_airport_operations")
    save_gold_table(airline_performance, "airline_performance")
    save_gold_table(route_performance, "route_performance")
    save_gold_table(hourly_flight_volume, "hourly_flight_volume")
    save_gold_table(gate_terminal_utilization, "gate_terminal_utilization")


if __name__ == "__main__":
    run_gold_creation()