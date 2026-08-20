from pathlib import Path
import json
import math

import numpy as np
import pandas as pd


# ==================================================================================================
# PATHS
# ==================================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FEATURES_DIR = BASE_DIR / "data" / "features"

INPUT_FILE = (
    FEATURES_DIR
    / "alesund_hourly_features_2024_2025.csv"
)

OUTPUT_FILE = (
    FEATURES_DIR
    / "alesund_ml_dataset.csv"
)

METADATA_FILE = (
    FEATURES_DIR
    / "alesund_ml_metadata.json"
)


# ==================================================================================================
# TARGET CONFIGURATION
# ==================================================================================================

TARGET_SOURCE_COLUMN = "future_total_events_1h"

TARGET_COLUMN = "traffic_level"

TARGET_NUMERIC_COLUMN = "traffic_level_numeric"


# ==================================================================================================
# FEATURE CONFIGURATION
# ==================================================================================================

BASE_FEATURES = [
    # ----------------------------------------------------------------------------------------------
    # Current-hour traffic
    # ----------------------------------------------------------------------------------------------

    "total_events",
    "arrivals",
    "departures",
    "unique_vessels",

    # ----------------------------------------------------------------------------------------------
    # Current traffic composition
    # ----------------------------------------------------------------------------------------------

    "passenger_events",
    "cargo_events",
    "fishing_events",
    "tanker_events",
    "auxiliary_events",
    "tug_events",

    # ----------------------------------------------------------------------------------------------
    # Calendar information
    # ----------------------------------------------------------------------------------------------

    "hour_local",
    "day_of_week",
    "month",
    "day_of_year",
    "is_weekend",

    # ----------------------------------------------------------------------------------------------
    # Total-event lag features
    # ----------------------------------------------------------------------------------------------

    "total_events_lag_1h",
    "total_events_lag_2h",
    "total_events_lag_3h",
    "total_events_lag_6h",
    "total_events_lag_24h",

    # ----------------------------------------------------------------------------------------------
    # Arrival lag features
    # ----------------------------------------------------------------------------------------------

    "arrivals_lag_1h",
    "arrivals_lag_2h",
    "arrivals_lag_3h",
    "arrivals_lag_24h",

    # ----------------------------------------------------------------------------------------------
    # Departure lag features
    # ----------------------------------------------------------------------------------------------

    "departures_lag_1h",
    "departures_lag_2h",
    "departures_lag_3h",
    "departures_lag_24h",

    # ----------------------------------------------------------------------------------------------
    # Vessel-count lags
    # ----------------------------------------------------------------------------------------------

    "unique_vessels_lag_1h",
    "unique_vessels_lag_24h",

    # ----------------------------------------------------------------------------------------------
    # Rolling features
    # ----------------------------------------------------------------------------------------------

    "total_events_rolling_mean_3h",
    "total_events_rolling_mean_6h",
    "total_events_rolling_mean_24h",

    "arrivals_rolling_mean_3h",
    "arrivals_rolling_mean_6h",
    "arrivals_rolling_mean_24h",
]


CYCLICAL_FEATURES = [
    "hour_sin",
    "hour_cos",

    "day_of_week_sin",
    "day_of_week_cos",

    "month_sin",
    "month_cos",
]


FINAL_FEATURES = (
    BASE_FEATURES
    + CYCLICAL_FEATURES
)


# ==================================================================================================
# LOAD DATA
# ==================================================================================================

def load_dataset() -> pd.DataFrame:

    print("=" * 100)
    print("OCEANEYE - PREPARE FINAL ML DATASET")
    print("=" * 100)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    dataframe = pd.read_csv(
        INPUT_FILE
    )

    dataframe["timestamp_utc"] = pd.to_datetime(
        dataframe["timestamp_utc"],
        errors="coerce",
        utc=True,
    )

    print(
        f"Loaded hourly observations: "
        f"{len(dataframe):,}"
    )

    return dataframe


# ==================================================================================================
# CYCLICAL TIME FEATURES
# ==================================================================================================

def add_cyclical_features(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    dataframe = dataframe.copy()

    # ----------------------------------------------------------------------------------------------
    # Hour of day
    #
    # 23:00 and 00:00 are actually close in time.
    #
    # A raw numeric encoding:
    #
    # 23 -> 0
    #
    # makes them appear far apart.
    #
    # Sin/cos encoding preserves the circular structure.
    # ----------------------------------------------------------------------------------------------

    dataframe["hour_sin"] = np.sin(
        2
        * np.pi
        * dataframe["hour_local"]
        / 24
    )

    dataframe["hour_cos"] = np.cos(
        2
        * np.pi
        * dataframe["hour_local"]
        / 24
    )

    # ----------------------------------------------------------------------------------------------
    # Day of week
    # ----------------------------------------------------------------------------------------------

    dataframe["day_of_week_sin"] = np.sin(
        2
        * np.pi
        * dataframe["day_of_week"]
        / 7
    )

    dataframe["day_of_week_cos"] = np.cos(
        2
        * np.pi
        * dataframe["day_of_week"]
        / 7
    )

    # ----------------------------------------------------------------------------------------------
    # Month
    # ----------------------------------------------------------------------------------------------

    dataframe["month_sin"] = np.sin(
        2
        * np.pi
        * (dataframe["month"] - 1)
        / 12
    )

    dataframe["month_cos"] = np.cos(
        2
        * np.pi
        * (dataframe["month"] - 1)
        / 12
    )

    return dataframe


# ==================================================================================================
# TARGET TIMESTAMP / LEAKAGE PROTECTION
# ==================================================================================================

def add_target_timestamp(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    dataframe = dataframe.copy()

    dataframe["target_timestamp_utc"] = (
        dataframe["timestamp_utc"]
        + pd.Timedelta(hours=1)
    )

    return dataframe


def determine_split(
    timestamp: pd.Timestamp,
) -> str | None:

    if pd.isna(timestamp):
        return None

    train_end = pd.Timestamp(
        "2025-01-01 00:00:00",
        tz="UTC",
    )

    validation_end = pd.Timestamp(
        "2025-10-01 00:00:00",
        tz="UTC",
    )

    dataset_end = pd.Timestamp(
        "2026-01-01 00:00:00",
        tz="UTC",
    )

    if timestamp < train_end:
        return "train"

    if timestamp < validation_end:
        return "validation"

    if timestamp < dataset_end:
        return "test"

    return None


def remove_split_boundary_leakage(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    dataframe = dataframe.copy()

    dataframe["target_split"] = (
        dataframe["target_timestamp_utc"]
        .apply(determine_split)
    )

    before = len(
        dataframe
    )

    # ----------------------------------------------------------------------------------------------
    # Observation and target must belong to the SAME temporal split.
    #
    # Example that gets removed:
    #
    # observation:
    # 2024-12-31 23:00  -> train
    #
    # target:
    # 2025-01-01 00:00  -> validation
    # ----------------------------------------------------------------------------------------------

    dataframe = dataframe.loc[
        dataframe["dataset_split"]
        ==
        dataframe["target_split"]
    ].copy()

    removed = (
        before
        - len(dataframe)
    )

    print()
    print(
        "Rows removed because target crosses "
        f"a dataset split boundary: {removed:,}"
    )

    return dataframe


# ==================================================================================================
# TARGET THRESHOLDS
# ==================================================================================================

def calculate_training_thresholds(
    dataframe: pd.DataFrame,
) -> tuple[float, float]:

    train_target = (
        dataframe.loc[
            dataframe["dataset_split"]
            == "train",
            TARGET_SOURCE_COLUMN,
        ]
        .dropna()
    )

    if train_target.empty:
        raise RuntimeError(
            "Training target is empty."
        )

    low_threshold = float(
        train_target.quantile(
            0.33
        )
    )

    high_threshold = float(
        train_target.quantile(
            0.67
        )
    )

    print()
    print("=" * 100)
    print("TARGET THRESHOLDS - TRAINING DATA ONLY")
    print("=" * 100)

    print(
        f"33rd percentile: "
        f"{low_threshold}"
    )

    print(
        f"67th percentile: "
        f"{high_threshold}"
    )

    return (
        low_threshold,
        high_threshold,
    )


# ==================================================================================================
# TARGET CLASSIFICATION
# ==================================================================================================

def classify_traffic(
    value: float,
    low_threshold: float,
    high_threshold: float,
) -> str | None:

    if pd.isna(value):
        return None

    if value <= low_threshold:
        return "LOW"

    if value <= high_threshold:
        return "MEDIUM"

    return "HIGH"


def add_target_class(
    dataframe: pd.DataFrame,
    low_threshold: float,
    high_threshold: float,
) -> pd.DataFrame:

    dataframe = dataframe.copy()

    dataframe[TARGET_COLUMN] = (
        dataframe[
            TARGET_SOURCE_COLUMN
        ]
        .apply(
            lambda value: classify_traffic(
                value=value,
                low_threshold=low_threshold,
                high_threshold=high_threshold,
            )
        )
    )

    class_mapping = {
        "LOW": 0,
        "MEDIUM": 1,
        "HIGH": 2,
    }

    dataframe[
        TARGET_NUMERIC_COLUMN
    ] = (
        dataframe[
            TARGET_COLUMN
        ]
        .map(class_mapping)
    )

    return dataframe


# ==================================================================================================
# REMOVE INVALID ML ROWS
# ==================================================================================================

def remove_incomplete_rows(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    dataframe = dataframe.copy()

    before = len(
        dataframe
    )

    required_columns = (
        FINAL_FEATURES
        + [
            TARGET_SOURCE_COLUMN,
            TARGET_COLUMN,
            TARGET_NUMERIC_COLUMN,
        ]
    )

    dataframe = (
        dataframe
        .dropna(
            subset=required_columns
        )
        .reset_index(drop=True)
    )

    removed = (
        before
        - len(dataframe)
    )

    print(
        f"Rows removed because of incomplete "
        f"features/target: {removed:,}"
    )

    return dataframe


# ==================================================================================================
# REPORTING
# ==================================================================================================

def print_class_distribution(
    dataframe: pd.DataFrame,
    split: str,
) -> None:

    subset = dataframe.loc[
        dataframe["dataset_split"]
        == split
    ]

    print()
    print(
        f"{split.upper()} CLASS DISTRIBUTION"
    )

    print("-" * 70)

    counts = (
        subset[
            TARGET_COLUMN
        ]
        .value_counts()
        .reindex(
            [
                "LOW",
                "MEDIUM",
                "HIGH",
            ]
        )
        .fillna(0)
        .astype(int)
    )

    percentages = (
        counts
        / counts.sum()
        * 100
    )

    for label in [
        "LOW",
        "MEDIUM",
        "HIGH",
    ]:

        print(
            f"{label:10} "
            f"{counts[label]:>6,} "
            f"({percentages[label]:>6.2f}%)"
        )


def print_summary(
    dataframe: pd.DataFrame,
    low_threshold: float,
    high_threshold: float,
) -> None:

    print()
    print("=" * 100)
    print("FINAL ML DATASET SUMMARY")
    print("=" * 100)

    print(
        f"Rows: "
        f"{len(dataframe):,}"
    )

    print(
        f"Features: "
        f"{len(FINAL_FEATURES)}"
    )

    print()
    print("TARGET")

    print("-" * 70)

    print(
        "Prediction horizon: "
        "1 hour"
    )

    print(
        f"Target source: "
        f"{TARGET_SOURCE_COLUMN}"
    )

    print()
    print(
        f"LOW: "
        f"0 <= events <= {low_threshold:g}"
    )

    print(
        f"MEDIUM: "
        f"{low_threshold:g} < events <= {high_threshold:g}"
    )

    print(
        f"HIGH: "
        f"events > {high_threshold:g}"
    )

    print()
    print("ROWS BY SPLIT")

    print("-" * 70)

    print(
        dataframe[
            "dataset_split"
        ]
        .value_counts()
        .to_string()
    )

    for split in [
        "train",
        "validation",
        "test",
    ]:

        print_class_distribution(
            dataframe=dataframe,
            split=split,
        )

    print()
    print("FEATURES")

    print("-" * 70)

    for index, feature in enumerate(
        FINAL_FEATURES,
        start=1,
    ):

        print(
            f"{index:02d}: "
            f"{feature}"
        )


# ==================================================================================================
# SAVE METADATA
# ==================================================================================================

def save_metadata(
    dataframe: pd.DataFrame,
    low_threshold: float,
    high_threshold: float,
) -> None:

    class_counts = {}

    for split in [
        "train",
        "validation",
        "test",
    ]:

        subset = dataframe.loc[
            dataframe["dataset_split"]
            == split
        ]

        counts = (
            subset[
                TARGET_COLUMN
            ]
            .value_counts()
            .to_dict()
        )

        class_counts[
            split
        ] = {
            key: int(value)
            for key, value in counts.items()
        }

    metadata = {
        "project": "OceanEye",

        "study_area": "Ålesund municipality, Norway",

        "prediction_horizon_hours": 1,

        "target_source": TARGET_SOURCE_COLUMN,

        "target_column": TARGET_COLUMN,

        "class_mapping": {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
        },

        "thresholds": {
            "low_max": low_threshold,
            "medium_max": high_threshold,
        },

        "threshold_method": (
            "33rd and 67th percentiles calculated "
            "using training data only"
        ),

        "temporal_split": {
            "train": "2024-01-01 through 2024-12-31",
            "validation": "2025-01-01 through 2025-09-30",
            "test": "2025-10-01 through 2025-12-31",
        },

        "features": FINAL_FEATURES,

        "feature_count": len(
            FINAL_FEATURES
        ),

        "row_count": len(
            dataframe
        ),

        "class_counts": class_counts,
    }

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4,
            ensure_ascii=False,
        )


# ==================================================================================================
# MAIN
# ==================================================================================================

def main() -> None:

    dataframe = load_dataset()

    # ----------------------------------------------------------------------------------------------
    # Add cyclical calendar features
    # ----------------------------------------------------------------------------------------------

    dataframe = add_cyclical_features(
        dataframe
    )

    # ----------------------------------------------------------------------------------------------
    # Determine the timestamp that the target represents
    # ----------------------------------------------------------------------------------------------

    dataframe = add_target_timestamp(
        dataframe
    )

    # ----------------------------------------------------------------------------------------------
    # Prevent temporal split leakage
    # ----------------------------------------------------------------------------------------------

    dataframe = remove_split_boundary_leakage(
        dataframe
    )

    # ----------------------------------------------------------------------------------------------
    # Calculate thresholds using TRAINING DATA ONLY
    # ----------------------------------------------------------------------------------------------

    (
        low_threshold,
        high_threshold,
    ) = calculate_training_thresholds(
        dataframe
    )

    # ----------------------------------------------------------------------------------------------
    # Generate LOW / MEDIUM / HIGH target
    # ----------------------------------------------------------------------------------------------

    dataframe = add_target_class(
        dataframe=dataframe,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )

    # ----------------------------------------------------------------------------------------------
    # Remove rows that do not have all required lag features / target.
    #
    # This primarily removes the first 24 hours because lag_24h
    # does not exist yet.
    # ----------------------------------------------------------------------------------------------

    dataframe = remove_incomplete_rows(
        dataframe
    )

    # ----------------------------------------------------------------------------------------------
    # Final chronological ordering
    # ----------------------------------------------------------------------------------------------

    dataframe = (
        dataframe
        .sort_values(
            "timestamp_utc"
        )
        .reset_index(drop=True)
    )

    # ----------------------------------------------------------------------------------------------
    # Save final dataset
    # ----------------------------------------------------------------------------------------------

    output_columns = (
        [
            "timestamp_utc",
            "target_timestamp_utc",
            "dataset_split",
        ]
        + FINAL_FEATURES
        + [
            TARGET_SOURCE_COLUMN,
            "future_arrivals_1h",
            "future_unique_vessels_1h",
            TARGET_COLUMN,
            TARGET_NUMERIC_COLUMN,
        ]
    )

    dataframe[
        output_columns
    ].to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    save_metadata(
        dataframe=dataframe,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )

    print_summary(
        dataframe=dataframe,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )

    print()
    print("=" * 100)
    print("OUTPUT FILES")
    print("=" * 100)

    print(
        f"ML dataset:\n"
        f"{OUTPUT_FILE}"
    )

    print()

    print(
        f"ML metadata:\n"
        f"{METADATA_FILE}"
    )


if __name__ == "__main__":
    main()