from pathlib import Path
import numpy as np
import pandas as pd


# ==================================================================================================
# PATHS
# ==================================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = BASE_DIR / "data" / "processed"
FEATURES_DIR = BASE_DIR / "data" / "features"

INPUT_FILE = (
    PROCESSED_DIR
    / "multi_area_voyages_2020_2025.csv"
)

EVENTS_OUTPUT_FILE = (
    FEATURES_DIR
    / "multi_area_events_2020_2025.csv"
)

HOURLY_OUTPUT_FILE = (
    FEATURES_DIR
    / "multi_area_hourly_features_2020_2025.csv"
)


# ==================================================================================================
# DATASET PERIOD
# ==================================================================================================

START_TIME = pd.Timestamp(
    "2020-01-01 00:00:00",
    tz="UTC",
)

END_TIME = pd.Timestamp(
    "2026-01-01 00:00:00",
    tz="UTC",
)

LOCAL_TIMEZONE = "Europe/Oslo"


# ==================================================================================================
# STUDY AREAS
# ==================================================================================================

STUDY_AREAS = [
    "Ålesund",
    "Bergen",
    "Tromsø",
    "Stavanger",
    "Kristiansund",
]


# Approximate municipality / city centroids.
# These are geographic context features, not port coordinates.

AREA_CENTROIDS = {
    "Ålesund": {
        "centroid_lat": 62.4722,
        "centroid_lon": 6.1495,
    },
    "Bergen": {
        "centroid_lat": 60.3913,
        "centroid_lon": 5.3221,
    },
    "Tromsø": {
        "centroid_lat": 69.6492,
        "centroid_lon": 18.9553,
    },
    "Stavanger": {
        "centroid_lat": 58.9700,
        "centroid_lon": 5.7331,
    },
    "Kristiansund": {
        "centroid_lat": 63.1103,
        "centroid_lon": 7.7281,
    },
}


# ==================================================================================================
# INPUT COLUMNS
# ==================================================================================================

USE_COLUMNS = [
    "seilas_id",
    "skips_id",
    "mmsi_nummer",
    "skipstype",
    "skipsgruppe",

    "study_area",

    "departure_time",
    "arrival_time",

    "departure_in_study_area",
    "arrival_in_study_area",
]


# ==================================================================================================
# HELPERS
# ==================================================================================================

def parse_boolean(
    series: pd.Series,
) -> pd.Series:

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


def normalize_identifier(
    series: pd.Series,
) -> pd.Series:

    cleaned = (
        series
        .astype("string")
        .str.strip()
        .str.replace(
            r"[,.]0$",
            "",
            regex=True,
        )
    )

    return cleaned.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "<NA>": pd.NA,
            "None": pd.NA,
        }
    )


def build_vessel_key(
    dataframe: pd.DataFrame,
) -> pd.Series:

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
# LOAD CLEAN MULTI-AREA VOYAGES
# ==================================================================================================

def load_dataset() -> pd.DataFrame:

    print("=" * 100)
    print("LOADING CLEAN MULTI-AREA DATASET")
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
            "study_area": "string",
        },
    )

    print(
        f"Loaded voyage-area rows: "
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

    dataframe[
        "departure_time"
    ] = pd.to_datetime(
        dataframe[
            "departure_time"
        ],
        errors="coerce",
        utc=True,
    )

    dataframe[
        "arrival_time"
    ] = pd.to_datetime(
        dataframe[
            "arrival_time"
        ],
        errors="coerce",
        utc=True,
    )

    dataframe[
        "vessel_key"
    ] = build_vessel_key(
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
    print("BUILDING MULTI-AREA MARITIME EVENTS")
    print("=" * 100)

    # ----------------------------------------------------------------------------------------------
    # Departures
    # ----------------------------------------------------------------------------------------------

    departures = voyages.loc[
        voyages[
            "departure_in_study_area"
        ]
    ].copy()

    departures = departures.loc[
        departures[
            "departure_time"
        ].notna()
    ].copy()

    departures = departures.rename(
        columns={
            "departure_time":
                "event_time",
        }
    )

    departures[
        "event_type"
    ] = "departure"

    departures = departures[
        [
            "study_area",
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
    # Arrivals
    # ----------------------------------------------------------------------------------------------

    arrivals = voyages.loc[
        voyages[
            "arrival_in_study_area"
        ]
    ].copy()

    arrivals = arrivals.loc[
        arrivals[
            "arrival_time"
        ].notna()
    ].copy()

    arrivals = arrivals.rename(
        columns={
            "arrival_time":
                "event_time",
        }
    )

    arrivals[
        "event_type"
    ] = "arrival"

    arrivals = arrivals[
        [
            "study_area",
            "seilas_id",
            "vessel_key",
            "mmsi_nummer",
            "skipstype",
            "skipsgruppe",
            "event_time",
            "event_type",
        ]
    ]

    events = pd.concat(
        [
            departures,
            arrivals,
        ],
        ignore_index=True,
    )

    # Keep only complete 2020-2025 period.
    # Some 2025 voyages arrive in early 2026.

    events = events.loc[
        (
            events[
                "event_time"
            ]
            >= START_TIME
        )
        &
        (
            events[
                "event_time"
            ]
            < END_TIME
        )
    ].copy()

    # Important:
    # study_area MUST be part of the duplicate key.
    #
    # The same voyage may correctly create events
    # in two different selected areas.

    before_duplicates = len(
        events
    )

    events = (
        events
        .drop_duplicates(
            subset=[
                "study_area",
                "seilas_id",
                "event_type",
                "event_time",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    duplicates_removed = (
        before_duplicates
        -
        len(events)
    )

    events[
        "hour_utc"
    ] = (
        events[
            "event_time"
        ]
        .dt.floor("h")
    )

    events = (
        events
        .sort_values(
            [
                "study_area",
                "event_time",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    print(
        f"Raw departure events: "
        f"{len(departures):,}"
    )

    print(
        f"Raw arrival events: "
        f"{len(arrivals):,}"
    )

    print(
        f"Events inside 2020-2025 period: "
        f"{len(events):,}"
    )

    print(
        f"Duplicate events removed: "
        f"{duplicates_removed:,}"
    )

    print()
    print("EVENTS BY STUDY AREA")
    print("-" * 70)

    print(
        events[
            "study_area"
        ]
        .value_counts()
        .to_string()
    )

    return events


# ==================================================================================================
# EVENT INDICATORS
# ==================================================================================================

def add_event_indicators(
    events: pd.DataFrame,
) -> pd.DataFrame:

    events = events.copy()

    group = (
        events[
            "skipsgruppe"
        ]
        .astype("string")
        .str.strip()
    )

    events[
        "is_passenger"
    ] = (
        group
        .eq("Passasjer")
        .fillna(False)
        .astype(int)
    )

    events[
        "is_cargo"
    ] = (
        group
        .eq("Last")
        .fillna(False)
        .astype(int)
    )

    events[
        "is_fishing"
    ] = (
        group
        .eq("Fisk")
        .fillna(False)
        .astype(int)
    )

    events[
        "is_tanker"
    ] = (
        group
        .eq("Tank")
        .fillna(False)
        .astype(int)
    )

    events[
        "is_auxiliary"
    ] = (
        group
        .eq("Auxiliary")
        .fillna(False)
        .astype(int)
    )

    events[
        "is_tug"
    ] = (
        group
        .eq("Slep")
        .fillna(False)
        .astype(int)
    )

    events[
        "is_arrival"
    ] = (
        events[
            "event_type"
        ]
        .eq("arrival")
        .astype(int)
    )

    events[
        "is_departure"
    ] = (
        events[
            "event_type"
        ]
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
    print("BUILDING MULTI-AREA HOURLY TIME SERIES")
    print("=" * 100)

    grouped = (
        events
        .groupby(
            [
                "study_area",
                "hour_utc",
            ]
        )
        .agg(
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
        .reset_index()
    )

    full_hour_index = pd.date_range(
        start=START_TIME,
        end=END_TIME,
        freq="h",
        inclusive="left",
    )

    area_frames = []

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

    for study_area in STUDY_AREAS:

        area_hourly = grouped.loc[
            grouped[
                "study_area"
            ]
            == study_area
        ].copy()

        area_hourly = (
            area_hourly
            .set_index(
                "hour_utc"
            )
            .reindex(
                full_hour_index
            )
        )

        area_hourly.index.name = (
            "timestamp_utc"
        )

        area_hourly[
            "study_area"
        ] = study_area

        for column in integer_columns:

            area_hourly[
                column
            ] = (
                area_hourly[
                    column
                ]
                .fillna(0)
                .astype(int)
            )

        area_hourly = (
            area_hourly
            .reset_index()
        )

        area_frames.append(
            area_hourly
        )

    hourly = pd.concat(
        area_frames,
        ignore_index=True,
    )

    hourly = (
        hourly
        .sort_values(
            [
                "study_area",
                "timestamp_utc",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    print(
        f"Study areas: "
        f"{hourly['study_area'].nunique()}"
    )

    print(
        f"Hourly observations: "
        f"{len(hourly):,}"
    )

    print(
        f"Hours per area: "
        f"{len(full_hour_index):,}"
    )

    return hourly


# ==================================================================================================
# LOCATION FEATURES
# ==================================================================================================

def add_location_features(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    hourly = hourly.copy()

    hourly[
        "centroid_lat"
    ] = hourly[
        "study_area"
    ].map(
        lambda area:
        AREA_CENTROIDS[
            area
        ][
            "centroid_lat"
        ]
    )

    hourly[
        "centroid_lon"
    ] = hourly[
        "study_area"
    ].map(
        lambda area:
        AREA_CENTROIDS[
            area
        ][
            "centroid_lon"
        ]
    )

    return hourly


# ==================================================================================================
# CALENDAR FEATURES
# ==================================================================================================

def add_calendar_features(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    hourly = hourly.copy()

    local_time = (
        hourly[
            "timestamp_utc"
        ]
        .dt.tz_convert(
            LOCAL_TIMEZONE
        )
    )

    hourly[
        "hour_local"
    ] = (
        local_time.dt.hour
    )

    hourly[
        "day_of_week"
    ] = (
        local_time.dt.dayofweek
    )

    hourly[
        "month"
    ] = (
        local_time.dt.month
    )

    hourly[
        "day_of_year"
    ] = (
        local_time.dt.dayofyear
    )

    hourly[
        "is_weekend"
    ] = (
        hourly[
            "day_of_week"
        ]
        .isin(
            [5, 6]
        )
        .astype(int)
    )

    # Cyclical temporal encoding

    hourly[
        "hour_sin"
    ] = np.sin(
        2
        * np.pi
        * hourly[
            "hour_local"
        ]
        / 24
    )

    hourly[
        "hour_cos"
    ] = np.cos(
        2
        * np.pi
        * hourly[
            "hour_local"
        ]
        / 24
    )

    hourly[
        "day_of_week_sin"
    ] = np.sin(
        2
        * np.pi
        * hourly[
            "day_of_week"
        ]
        / 7
    )

    hourly[
        "day_of_week_cos"
    ] = np.cos(
        2
        * np.pi
        * hourly[
            "day_of_week"
        ]
        / 7
    )

    hourly[
        "month_sin"
    ] = np.sin(
        2
        * np.pi
        * (
            hourly[
                "month"
            ]
            - 1
        )
        / 12
    )

    hourly[
        "month_cos"
    ] = np.cos(
        2
        * np.pi
        * (
            hourly[
                "month"
            ]
            - 1
        )
        / 12
    )

    return hourly


# ==================================================================================================
# LAG / ROLLING FEATURES
# ==================================================================================================

def add_lag_features(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    hourly = (
        hourly
        .sort_values(
            [
                "study_area",
                "timestamp_utc",
            ]
        )
        .copy()
    )

    grouped = hourly.groupby(
        "study_area",
        group_keys=False,
    )

    # ----------------------------------------------------------------------------------------------
    # Total event lags
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
        ] = grouped[
            "total_events"
        ].shift(
            lag
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
        ] = grouped[
            "arrivals"
        ].shift(
            lag
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
        ] = grouped[
            "departures"
        ].shift(
            lag
        )

    # ----------------------------------------------------------------------------------------------
    # Unique vessel lags
    # ----------------------------------------------------------------------------------------------

    hourly[
        "unique_vessels_lag_1h"
    ] = grouped[
        "unique_vessels"
    ].shift(
        1
    )

    hourly[
        "unique_vessels_lag_24h"
    ] = grouped[
        "unique_vessels"
    ].shift(
        24
    )

    # ----------------------------------------------------------------------------------------------
    # Rolling means.
    #
    # IMPORTANT:
    # shift(1) prevents current-hour leakage.
    #
    # Also critically important:
    # calculations are performed separately for every study_area.
    # ----------------------------------------------------------------------------------------------

    hourly[
        "total_events_rolling_mean_3h"
    ] = (
        grouped[
            "total_events"
        ]
        .transform(
            lambda series:
                series
                .shift(1)
                .rolling(
                    window=3,
                    min_periods=1,
                )
                .mean()
        )
    )

    hourly[
        "total_events_rolling_mean_6h"
    ] = (
        grouped[
            "total_events"
        ]
        .transform(
            lambda series:
                series
                .shift(1)
                .rolling(
                    window=6,
                    min_periods=1,
                )
                .mean()
        )
    )

    hourly[
        "total_events_rolling_mean_24h"
    ] = (
        grouped[
            "total_events"
        ]
        .transform(
            lambda series:
                series
                .shift(1)
                .rolling(
                    window=24,
                    min_periods=1,
                )
                .mean()
        )
    )

    hourly[
        "arrivals_rolling_mean_3h"
    ] = (
        grouped[
            "arrivals"
        ]
        .transform(
            lambda series:
                series
                .shift(1)
                .rolling(
                    window=3,
                    min_periods=1,
                )
                .mean()
        )
    )

    hourly[
        "arrivals_rolling_mean_6h"
    ] = (
        grouped[
            "arrivals"
        ]
        .transform(
            lambda series:
                series
                .shift(1)
                .rolling(
                    window=6,
                    min_periods=1,
                )
                .mean()
        )
    )

    hourly[
        "arrivals_rolling_mean_24h"
    ] = (
        grouped[
            "arrivals"
        ]
        .transform(
            lambda series:
                series
                .shift(1)
                .rolling(
                    window=24,
                    min_periods=1,
                )
                .mean()
        )
    )

    return hourly


# ==================================================================================================
# FUTURE TARGETS
# ==================================================================================================

def add_future_targets(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    hourly = (
        hourly
        .sort_values(
            [
                "study_area",
                "timestamp_utc",
            ]
        )
        .copy()
    )

    grouped = hourly.groupby(
        "study_area",
        group_keys=False,
    )

    hourly[
        "future_total_events_1h"
    ] = grouped[
        "total_events"
    ].shift(
        -1
    )

    hourly[
        "future_arrivals_1h"
    ] = grouped[
        "arrivals"
    ].shift(
        -1
    )

    hourly[
        "future_unique_vessels_1h"
    ] = grouped[
        "unique_vessels"
    ].shift(
        -1
    )

    return hourly


# ==================================================================================================
# TEMPORAL SPLIT
# ==================================================================================================

def add_split_labels(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    hourly = hourly.copy()

    # Main Multi-Area V2 temporal experiment:
    #
    # TRAIN      = 2020-2023
    # VALIDATION = 2024
    # TEST       = 2025
    #
    # No random shuffle is used.

    validation_start = pd.Timestamp(
        "2024-01-01 00:00:00",
        tz="UTC",
    )

    test_start = pd.Timestamp(
        "2025-01-01 00:00:00",
        tz="UTC",
    )

    hourly[
        "dataset_split"
    ] = "train"

    hourly.loc[
        hourly[
            "timestamp_utc"
        ]
        >= validation_start,
        "dataset_split",
    ] = "validation"

    hourly.loc[
        hourly[
            "timestamp_utc"
        ]
        >= test_start,
        "dataset_split",
    ] = "test"

    return hourly


# ==================================================================================================
# REPORTING
# ==================================================================================================

def print_area_summary(
    hourly: pd.DataFrame,
) -> None:

    print()
    print("=" * 100)
    print("MULTI-AREA HOURLY DATASET SUMMARY")
    print("=" * 100)

    print(
        f"Rows: "
        f"{len(hourly):,}"
    )

    print(
        f"Study areas: "
        f"{hourly['study_area'].nunique()}"
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
    print("ROWS BY SPLIT")
    print("-" * 70)

    print(
        hourly[
            "dataset_split"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("ROWS BY AREA / SPLIT")
    print("-" * 70)

    print(
        pd.crosstab(
            hourly[
                "study_area"
            ],
            hourly[
                "dataset_split"
            ],
        ).to_string()
    )

    print()
    print("TOTAL EVENTS BY AREA")
    print("-" * 70)

    print(
        hourly
        .groupby(
            "study_area"
        )[
            "total_events"
        ]
        .sum()
        .sort_values(
            ascending=False
        )
        .to_string()
    )

    print()
    print("ZERO-EVENT HOURS BY AREA")
    print("-" * 70)

    summary_rows = []

    for study_area in STUDY_AREAS:

        area = hourly.loc[
            hourly[
                "study_area"
            ]
            == study_area
        ]

        zero_hours = int(
            (
                area[
                    "total_events"
                ]
                == 0
            )
            .sum()
        )

        summary_rows.append(
            {
                "study_area":
                    study_area,

                "rows":
                    len(area),

                "zero_hours":
                    zero_hours,

                "zero_pct":
                    (
                        zero_hours
                        / len(area)
                        * 100
                    ),

                "mean_events":
                    area[
                        "total_events"
                    ].mean(),

                "max_events":
                    area[
                        "total_events"
                    ].max(),
            }
        )

    summary = pd.DataFrame(
        summary_rows
    )

    print(
        summary.to_string(
            index=False,
            formatters={
                "zero_pct":
                    lambda value:
                        f"{value:.2f}%",

                "mean_events":
                    lambda value:
                        f"{value:.3f}",
            },
        )
    )

    print()
    print("TARGET DISTRIBUTION - TRAIN ONLY")
    print("-" * 70)

    train = hourly.loc[
        hourly[
            "dataset_split"
        ]
        == "train"
    ]

    for study_area in STUDY_AREAS:

        area_train = train.loc[
            train[
                "study_area"
            ]
            == study_area,
            "future_total_events_1h",
        ].dropna()

        print()
        print(
            study_area
        )

        print(
            f"  count = "
            f"{len(area_train):,}"
        )

        print(
            f"  mean  = "
            f"{area_train.mean():.3f}"
        )

        print(
            f"  q33   = "
            f"{area_train.quantile(0.33):.3f}"
        )

        print(
            f"  q67   = "
            f"{area_train.quantile(0.67):.3f}"
        )

        print(
            f"  q90   = "
            f"{area_train.quantile(0.90):.3f}"
        )

        print(
            f"  max   = "
            f"{area_train.max():.0f}"
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

    events.to_csv(
        EVENTS_OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    hourly = build_hourly_dataset(
        events
    )

    hourly = add_location_features(
        hourly
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

    hourly.to_csv(
        HOURLY_OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print_area_summary(
        hourly
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