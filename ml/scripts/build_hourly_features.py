from pathlib import Path

import pandas as pd


# ==================================================================================================
# PATHS
# ==================================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = BASE_DIR / "data" / "processed"
FEATURES_DIR = BASE_DIR / "data" / "features"

INPUT_FILE = (
    PROCESSED_DIR
    / "alesund_voyages_2024_2025_ml.csv"
)

EVENTS_OUTPUT_FILE = (
    FEATURES_DIR
    / "alesund_events_2024_2025.csv"
)

HOURLY_OUTPUT_FILE = (
    FEATURES_DIR
    / "alesund_hourly_features_2024_2025.csv"
)


# ==================================================================================================
# DATASET PERIOD
# ==================================================================================================

START_TIME = pd.Timestamp(
    "2024-01-01 00:00:00",
    tz="UTC",
)

END_TIME = pd.Timestamp(
    "2026-01-01 00:00:00",
    tz="UTC",
)

LOCAL_TIMEZONE = "Europe/Oslo"


# ==================================================================================================
# COLUMNS REQUIRED FROM CLEAN DATASET
# ==================================================================================================

USE_COLUMNS = [
    "seilas_id",
    "skips_id",
    "mmsi_nummer",
    "skipstype",
    "skipsgruppe",

    "departure_time",
    "arrival_time",

    "departure_in_study_area",
    "arrival_in_study_area",
]


# ==================================================================================================
# HELPERS
# ==================================================================================================

def parse_boolean(series: pd.Series) -> pd.Series:
    """
    Safely convert CSV boolean values to Python/Pandas booleans.

    Accepted true examples:
        True
        true
        1
        t
        yes

    Everything else becomes False.
    """

    normalized = (
        series
        .astype("string")
        .str.strip()
        .str.lower()
    )

    return normalized.isin(
        [
            "true",
            "1",
            "t",
            "yes",
            "y",
        ]
    )


def normalize_identifier(series: pd.Series) -> pd.Series:
    """
    Normalize identifiers that may have been interpreted
    with decimal artifacts.
    """

    return (
        series
        .astype("string")
        .str.strip()
        .str.replace(
            r"[,.]0$",
            "",
            regex=True,
        )
    )


def build_vessel_key(dataframe: pd.DataFrame) -> pd.Series:
    """
    MMSI is the preferred vessel identifier.

    A very small number of records have no valid MMSI,
    so skips_id is used as a fallback.
    """

    mmsi = normalize_identifier(
        dataframe["mmsi_nummer"]
    )

    vessel_id = normalize_identifier(
        dataframe["skips_id"]
    )

    fallback = (
        "SHIP_"
        + vessel_id.fillna("UNKNOWN")
    )

    return mmsi.fillna(
        fallback
    )


# ==================================================================================================
# LOAD DATA
# ==================================================================================================

def load_dataset() -> pd.DataFrame:

    print("=" * 100)
    print("LOADING CLEAN ÅLESUND DATASET")
    print("=" * 100)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    dataframe = pd.read_csv(
        INPUT_FILE,
        usecols=USE_COLUMNS,
        dtype={
            "seilas_id": "string",
            "skips_id": "string",
            "mmsi_nummer": "string",
            "skipstype": "string",
            "skipsgruppe": "string",
        },
    )

    print(
        f"Loaded rows: "
        f"{len(dataframe):,}"
    )

    dataframe[
        "departure_in_study_area"
    ] = parse_boolean(
        dataframe[
            "departure_in_study_area"
        ]
    )

    dataframe[
        "arrival_in_study_area"
    ] = parse_boolean(
        dataframe[
            "arrival_in_study_area"
        ]
    )

    dataframe["departure_time"] = pd.to_datetime(
        dataframe["departure_time"],
        errors="coerce",
        utc=True,
    )

    dataframe["arrival_time"] = pd.to_datetime(
        dataframe["arrival_time"],
        errors="coerce",
        utc=True,
    )

    dataframe["vessel_key"] = build_vessel_key(
        dataframe
    )

    return dataframe


# ==================================================================================================
# BUILD EVENT TABLE
# ==================================================================================================

def build_events(
    voyages: pd.DataFrame,
) -> pd.DataFrame:

    print()
    print("=" * 100)
    print("BUILDING MARITIME EVENTS")
    print("=" * 100)

    # ----------------------------------------------------------------------------------------------
    # Departure events
    # ----------------------------------------------------------------------------------------------

    departures = voyages.loc[
        voyages["departure_in_study_area"]
    ].copy()

    departures = departures.loc[
        departures["departure_time"].notna()
    ].copy()

    departures = departures.rename(
        columns={
            "departure_time": "event_time",
        }
    )

    departures["event_type"] = "departure"

    departures = departures[
        [
            "seilas_id",
            "vessel_key",
            "mmsi_nummer",
            "skipstype",
            "skipsgruppe",
            "event_time",
            "event_type",
        ]
    ]

    # ----------------------------------------------------------------------------------------------
    # Arrival events
    # ----------------------------------------------------------------------------------------------

    arrivals = voyages.loc[
        voyages["arrival_in_study_area"]
    ].copy()

    arrivals = arrivals.loc[
        arrivals["arrival_time"].notna()
    ].copy()

    arrivals = arrivals.rename(
        columns={
            "arrival_time": "event_time",
        }
    )

    arrivals["event_type"] = "arrival"

    arrivals = arrivals[
        [
            "seilas_id",
            "vessel_key",
            "mmsi_nummer",
            "skipstype",
            "skipsgruppe",
            "event_time",
            "event_type",
        ]
    ]

    # ----------------------------------------------------------------------------------------------
    # Combine
    # ----------------------------------------------------------------------------------------------

    events = pd.concat(
        [
            departures,
            arrivals,
        ],
        ignore_index=True,
    )

    # ----------------------------------------------------------------------------------------------
    # Restrict to complete calendar years:
    #
    # 2024-01-01 inclusive
    # 2026-01-01 exclusive
    #
    # Some 2025 voyages arrive in early 2026.
    # We exclude those because 2026 is incomplete.
    # ----------------------------------------------------------------------------------------------

    events = events.loc[
        (events["event_time"] >= START_TIME)
        &
        (events["event_time"] < END_TIME)
    ].copy()

    # ----------------------------------------------------------------------------------------------
    # Remove exact event duplicates
    # ----------------------------------------------------------------------------------------------

    before_duplicates = len(
        events
    )

    events = (
        events
        .drop_duplicates(
            subset=[
                "seilas_id",
                "event_type",
                "event_time",
            ]
        )
        .reset_index(drop=True)
    )

    duplicates_removed = (
        before_duplicates
        -
        len(events)
    )

    # ----------------------------------------------------------------------------------------------
    # Hour bin
    # ----------------------------------------------------------------------------------------------

    events["hour_utc"] = (
        events["event_time"]
        .dt.floor("h")
    )

    events = (
        events
        .sort_values(
            "event_time"
        )
        .reset_index(drop=True)
    )

    print(
        f"Departure events: "
        f"{len(departures):,}"
    )

    print(
        f"Arrival events: "
        f"{len(arrivals):,}"
    )

    print(
        f"Events inside 2024-2025 period: "
        f"{len(events):,}"
    )

    print(
        f"Duplicate events removed: "
        f"{duplicates_removed:,}"
    )

    return events


# ==================================================================================================
# ADD VESSEL GROUP INDICATORS
# ==================================================================================================

def add_event_indicators(
    events: pd.DataFrame,
) -> pd.DataFrame:

    events = events.copy()

    group = (
        events["skipsgruppe"]
        .astype("string")
        .str.strip()
    )

    events["is_passenger"] = (
        group.eq("Passasjer")
        .fillna(False)
        .astype(int)
    )

    events["is_cargo"] = (
        group.eq("Last")
        .fillna(False)
        .astype(int)
    )

    events["is_fishing"] = (
        group.eq("Fisk")
        .fillna(False)
        .astype(int)
    )

    events["is_tanker"] = (
        group.eq("Tank")
        .fillna(False)
        .astype(int)
    )

    events["is_auxiliary"] = (
        group.eq("Auxiliary")
        .fillna(False)
        .astype(int)
    )

    events["is_tug"] = (
        group.eq("Slep")
        .fillna(False)
        .astype(int)
    )

    events["is_arrival"] = (
        events["event_type"]
        .eq("arrival")
        .astype(int)
    )

    events["is_departure"] = (
        events["event_type"]
        .eq("departure")
        .astype(int)
    )

    return events


# ==================================================================================================
# HOURLY AGGREGATION
# ==================================================================================================

def build_hourly_dataset(
    events: pd.DataFrame,
) -> pd.DataFrame:

    print()
    print("=" * 100)
    print("BUILDING HOURLY TIME SERIES")
    print("=" * 100)

    grouped = events.groupby(
        "hour_utc"
    )

    hourly = grouped.agg(
        total_events=(
            "event_type",
            "size",
        ),

        arrivals=(
            "is_arrival",
            "sum",
        ),

        departures=(
            "is_departure",
            "sum",
        ),

        unique_vessels=(
            "vessel_key",
            "nunique",
        ),

        passenger_events=(
            "is_passenger",
            "sum",
        ),

        cargo_events=(
            "is_cargo",
            "sum",
        ),

        fishing_events=(
            "is_fishing",
            "sum",
        ),

        tanker_events=(
            "is_tanker",
            "sum",
        ),

        auxiliary_events=(
            "is_auxiliary",
            "sum",
        ),

        tug_events=(
            "is_tug",
            "sum",
        ),
    )

    # ----------------------------------------------------------------------------------------------
    # Create a COMPLETE hourly timeline.
    #
    # Hours with no port activity are important observations
    # and must not disappear from the ML dataset.
    # ----------------------------------------------------------------------------------------------

    full_hour_index = pd.date_range(
        start=START_TIME,
        end=END_TIME,
        freq="h",
        inclusive="left",
    )

    hourly = hourly.reindex(
        full_hour_index,
        fill_value=0,
    )

    hourly.index.name = "timestamp_utc"

    hourly = hourly.reset_index()

    integer_columns = [
        "total_events",
        "arrivals",
        "departures",
        "unique_vessels",
        "passenger_events",
        "cargo_events",
        "fishing_events",
        "tanker_events",
        "auxiliary_events",
        "tug_events",
    ]

    for column in integer_columns:
        hourly[column] = (
            hourly[column]
            .fillna(0)
            .astype(int)
        )

    print(
        f"Hourly observations: "
        f"{len(hourly):,}"
    )

    return hourly


# ==================================================================================================
# TIME FEATURES
# ==================================================================================================

def add_calendar_features(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    hourly = hourly.copy()

    local_time = (
        hourly["timestamp_utc"]
        .dt.tz_convert(
            LOCAL_TIMEZONE
        )
    )

    hourly["hour_local"] = (
        local_time.dt.hour
    )

    hourly["day_of_week"] = (
        local_time.dt.dayofweek
    )

    hourly["month"] = (
        local_time.dt.month
    )

    hourly["day_of_year"] = (
        local_time.dt.dayofyear
    )

    hourly["is_weekend"] = (
        hourly["day_of_week"]
        .isin([5, 6])
        .astype(int)
    )

    return hourly


# ==================================================================================================
# LAG FEATURES
# ==================================================================================================

def add_lag_features(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    hourly = hourly.copy()

    # ----------------------------------------------------------------------------------------------
    # Total traffic lags
    # ----------------------------------------------------------------------------------------------

    for lag in [
        1,
        2,
        3,
        6,
        24,
    ]:

        hourly[
            f"total_events_lag_{lag}h"
        ] = (
            hourly["total_events"]
            .shift(lag)
        )

    # ----------------------------------------------------------------------------------------------
    # Arrival lags
    # ----------------------------------------------------------------------------------------------

    for lag in [
        1,
        2,
        3,
        24,
    ]:

        hourly[
            f"arrivals_lag_{lag}h"
        ] = (
            hourly["arrivals"]
            .shift(lag)
        )

    # ----------------------------------------------------------------------------------------------
    # Departure lags
    # ----------------------------------------------------------------------------------------------

    for lag in [
        1,
        2,
        3,
        24,
    ]:

        hourly[
            f"departures_lag_{lag}h"
        ] = (
            hourly["departures"]
            .shift(lag)
        )

    # ----------------------------------------------------------------------------------------------
    # Unique vessel lags
    # ----------------------------------------------------------------------------------------------

    hourly[
        "unique_vessels_lag_1h"
    ] = (
        hourly["unique_vessels"]
        .shift(1)
    )

    hourly[
        "unique_vessels_lag_24h"
    ] = (
        hourly["unique_vessels"]
        .shift(24)
    )

    # ----------------------------------------------------------------------------------------------
    # Rolling features.
    #
    # IMPORTANT:
    # shift(1) is deliberately used BEFORE rolling.
    #
    # This means that an observation at time t only uses
    # information available before t.
    #
    # It prevents future/current-target leakage.
    # ----------------------------------------------------------------------------------------------

    historical_total = (
        hourly["total_events"]
        .shift(1)
    )

    hourly[
        "total_events_rolling_mean_3h"
    ] = (
        historical_total
        .rolling(
            window=3,
            min_periods=1,
        )
        .mean()
    )

    hourly[
        "total_events_rolling_mean_6h"
    ] = (
        historical_total
        .rolling(
            window=6,
            min_periods=1,
        )
        .mean()
    )

    hourly[
        "total_events_rolling_mean_24h"
    ] = (
        historical_total
        .rolling(
            window=24,
            min_periods=1,
        )
        .mean()
    )

    historical_arrivals = (
        hourly["arrivals"]
        .shift(1)
    )

    hourly[
        "arrivals_rolling_mean_3h"
    ] = (
        historical_arrivals
        .rolling(
            window=3,
            min_periods=1,
        )
        .mean()
    )

    hourly[
        "arrivals_rolling_mean_6h"
    ] = (
        historical_arrivals
        .rolling(
            window=6,
            min_periods=1,
        )
        .mean()
    )

    hourly[
        "arrivals_rolling_mean_24h"
    ] = (
        historical_arrivals
        .rolling(
            window=24,
            min_periods=1,
        )
        .mean()
    )

    return hourly


# ==================================================================================================
# FUTURE TARGET VALUES
# ==================================================================================================

def add_future_targets(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    hourly = hourly.copy()

    # ----------------------------------------------------------------------------------------------
    # Potential target A:
    # total maritime events during the NEXT hour
    # ----------------------------------------------------------------------------------------------

    hourly[
        "future_total_events_1h"
    ] = (
        hourly["total_events"]
        .shift(-1)
    )

    # ----------------------------------------------------------------------------------------------
    # Potential target B:
    # arrivals during the NEXT hour
    #
    # This may become our preferred final target because
    # arrival_time is more reliable than estimated departure time.
    # ----------------------------------------------------------------------------------------------

    hourly[
        "future_arrivals_1h"
    ] = (
        hourly["arrivals"]
        .shift(-1)
    )

    # ----------------------------------------------------------------------------------------------
    # Potential target C:
    # unique-vessel activity in the next hour
    # ----------------------------------------------------------------------------------------------

    hourly[
        "future_unique_vessels_1h"
    ] = (
        hourly["unique_vessels"]
        .shift(-1)
    )

    return hourly


# ==================================================================================================
# DATASET SPLIT LABELS
# ==================================================================================================

def add_split_labels(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    hourly = hourly.copy()

    hourly["dataset_split"] = "train"

    # 2024:
    #
    # TRAIN
    #
    # 2025-01-01 -> 2025-09-30:
    #
    # VALIDATION
    #
    # 2025-10-01 -> 2025-12-31:
    #
    # TEST

    validation_start = pd.Timestamp(
        "2025-01-01 00:00:00",
        tz="UTC",
    )

    test_start = pd.Timestamp(
        "2025-10-01 00:00:00",
        tz="UTC",
    )

    hourly.loc[
        hourly["timestamp_utc"]
        >= validation_start,
        "dataset_split",
    ] = "validation"

    hourly.loc[
        hourly["timestamp_utc"]
        >= test_start,
        "dataset_split",
    ] = "test"

    return hourly


# ==================================================================================================
# REPORTING
# ==================================================================================================

def print_distribution(
    series: pd.Series,
    name: str,
) -> None:

    clean = series.dropna()

    print()
    print(name)
    print("-" * 60)

    print(
        f"Count: "
        f"{len(clean):,}"
    )

    print(
        f"Mean: "
        f"{clean.mean():.3f}"
    )

    print(
        f"Median: "
        f"{clean.median():.3f}"
    )

    print(
        f"Std: "
        f"{clean.std():.3f}"
    )

    print(
        f"Min: "
        f"{clean.min():.0f}"
    )

    print(
        f"Max: "
        f"{clean.max():.0f}"
    )

    print()
    print("QUANTILES")

    quantiles = clean.quantile(
        [
            0.10,
            0.25,
            0.33,
            0.50,
            0.67,
            0.75,
            0.90,
            0.95,
            0.99,
        ]
    )

    print(
        quantiles.to_string()
    )

    print()
    print("MOST COMMON VALUES")

    print(
        clean
        .value_counts()
        .sort_index()
        .head(30)
        .to_string()
    )


def print_summary(
    events: pd.DataFrame,
    hourly: pd.DataFrame,
) -> None:

    print()
    print("=" * 100)
    print("HOURLY FEATURE DATASET SUMMARY")
    print("=" * 100)

    print(
        f"Events: "
        f"{len(events):,}"
    )

    print(
        f"Hourly observations: "
        f"{len(hourly):,}"
    )

    print(
        f"Start: "
        f"{hourly['timestamp_utc'].min()}"
    )

    print(
        f"End: "
        f"{hourly['timestamp_utc'].max()}"
    )

    print()
    print("DATASET SPLITS")
    print("-" * 60)

    print(
        hourly[
            "dataset_split"
        ]
        .value_counts()
        .to_string()
    )

    zero_event_hours = int(
        (
            hourly["total_events"] == 0
        )
        .sum()
    )

    print()
    print(
        f"Hours with zero events: "
        f"{zero_event_hours:,}"
    )

    print(
        f"Zero-event percentage: "
        f"{(
            zero_event_hours
            / len(hourly)
            * 100
        ):.2f}%"
    )

    print_distribution(
        hourly["total_events"],
        "CURRENT TOTAL EVENTS",
    )

    print_distribution(
        hourly["arrivals"],
        "CURRENT ARRIVALS",
    )

    print_distribution(
        hourly["unique_vessels"],
        "CURRENT UNIQUE VESSELS",
    )

    # ----------------------------------------------------------------------------------------------
    # Very important:
    # examine targets using TRAIN period only.
    #
    # Thresholds for LOW / MEDIUM / HIGH must later be derived
    # from training data only to avoid data leakage.
    # ----------------------------------------------------------------------------------------------

    train = hourly.loc[
        hourly["dataset_split"]
        == "train"
    ]

    print()
    print("=" * 100)
    print("TRAINING-PERIOD TARGET DISTRIBUTIONS")
    print("=" * 100)

    print_distribution(
        train[
            "future_total_events_1h"
        ],
        "FUTURE TOTAL EVENTS +1H - TRAIN ONLY",
    )

    print_distribution(
        train[
            "future_arrivals_1h"
        ],
        "FUTURE ARRIVALS +1H - TRAIN ONLY",
    )

    print_distribution(
        train[
            "future_unique_vessels_1h"
        ],
        "FUTURE UNIQUE VESSELS +1H - TRAIN ONLY",
    )


# ==================================================================================================
# MAIN
# ==================================================================================================

def main() -> None:

    FEATURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    voyages = load_dataset()

    events = build_events(
        voyages
    )

    events = add_event_indicators(
        events
    )

    # ----------------------------------------------------------------------------------------------
    # Save normalized event-level dataset
    # ----------------------------------------------------------------------------------------------

    events.to_csv(
        EVENTS_OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    hourly = build_hourly_dataset(
        events
    )

    hourly = add_calendar_features(
        hourly
    )

    hourly = add_lag_features(
        hourly
    )

    hourly = add_future_targets(
        hourly
    )

    hourly = add_split_labels(
        hourly
    )

    # ----------------------------------------------------------------------------------------------
    # First 24 hours do not have all lag features.
    #
    # The final row has no t+1 target.
    #
    # Do NOT globally drop them yet.
    # Keeping them is useful for inspection.
    # Training code will select valid rows.
    # ----------------------------------------------------------------------------------------------

    hourly.to_csv(
        HOURLY_OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print_summary(
        events=events,
        hourly=hourly,
    )

    print()
    print("=" * 100)
    print("OUTPUT FILES")
    print("=" * 100)

    print(
        f"Event dataset:\n"
        f"{EVENTS_OUTPUT_FILE}"
    )

    print()

    print(
        f"Hourly feature dataset:\n"
        f"{HOURLY_OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()