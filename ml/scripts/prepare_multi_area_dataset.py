from pathlib import Path
import json

import numpy as np
import pandas as pd


# ======================================================================================
# PATHS
# ======================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FEATURES_DIR = BASE_DIR / "data" / "features"

INPUT_FILE = (
    FEATURES_DIR
    / "multi_area_hourly_features_2020_2025.csv"
)

OUTPUT_FILE = (
    FEATURES_DIR
    / "multi_area_ml_dataset.csv"
)

METADATA_FILE = (
    FEATURES_DIR
    / "multi_area_ml_metadata.json"
)


# ======================================================================================
# TEMPORAL SPLIT
# ======================================================================================

TRAIN_END = pd.Timestamp(
    "2025-01-01 00:00:00",
    tz="UTC",
)

VALIDATION_END = pd.Timestamp(
    "2025-10-01 00:00:00",
    tz="UTC",
)

DATA_END = pd.Timestamp(
    "2026-01-01 00:00:00",
    tz="UTC",
)


# ======================================================================================
# FEATURES
# ======================================================================================

NUMERIC_FEATURES = [
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

    "hour_local",
    "day_of_week",
    "month",
    "day_of_year",
    "is_weekend",

    "total_events_lag_1h",
    "total_events_lag_2h",
    "total_events_lag_3h",
    "total_events_lag_6h",
    "total_events_lag_24h",

    "arrivals_lag_1h",
    "arrivals_lag_2h",
    "arrivals_lag_3h",
    "arrivals_lag_24h",

    "departures_lag_1h",
    "departures_lag_2h",
    "departures_lag_3h",
    "departures_lag_24h",

    "unique_vessels_lag_1h",
    "unique_vessels_lag_24h",

    "total_events_rolling_mean_3h",
    "total_events_rolling_mean_6h",
    "total_events_rolling_mean_24h",

    "arrivals_rolling_mean_3h",
    "arrivals_rolling_mean_6h",
    "arrivals_rolling_mean_24h",

    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "month_sin",
    "month_cos",

    "centroid_lat",
    "centroid_lon",
]

CATEGORICAL_FEATURES = [
    "study_area",
]

TARGET_COLUMN = "future_total_events_1h"


# ======================================================================================
# LOAD DATASET
# ======================================================================================

def load_dataset():

    print("=" * 100)
    print("LOADING MULTI-AREA HOURLY DATASET")
    print("=" * 100)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        errors="coerce",
        utc=True,
    )

    print(
        f"Loaded rows: {len(df):,}"
    )

    return df


# ======================================================================================
# TEMPORAL SPLIT
# ======================================================================================

def assign_temporal_split(df):

    df = df.copy()

    df["dataset_split"] = pd.NA

    train_mask = (
        df["timestamp_utc"]
        < TRAIN_END
    )

    validation_mask = (
        (df["timestamp_utc"] >= TRAIN_END)
        &
        (df["timestamp_utc"] < VALIDATION_END)
    )

    test_mask = (
        (df["timestamp_utc"] >= VALIDATION_END)
        &
        (df["timestamp_utc"] < DATA_END)
    )

    df.loc[
        train_mask,
        "dataset_split",
    ] = "train"

    df.loc[
        validation_mask,
        "dataset_split",
    ] = "validation"

    df.loc[
        test_mask,
        "dataset_split",
    ] = "test"

    df = df.loc[
        df["dataset_split"].notna()
    ].copy()

    return df


# ======================================================================================
# REMOVE INVALID BOUNDARY ROWS
# ======================================================================================

def remove_boundary_rows(df):

    """
    Lag features must never cross study-area boundaries.

    The first 24 hours of each area's complete time series do not have
    a complete 24-hour history and are therefore removed.

    The final hour of each study area has no t+1 target and is also removed.
    """

    before = len(df)

    required_columns = (
        NUMERIC_FEATURES
        + [TARGET_COLUMN]
    )

    df = df.dropna(
        subset=required_columns
    ).copy()

    removed = before - len(df)

    print(
        f"Rows removed because of incomplete "
        f"lag/target history: {removed:,}"
    )

    return df


# ======================================================================================
# AREA-SPECIFIC HIGH THRESHOLDS
# ======================================================================================

def calculate_area_thresholds(df):

    print()
    print("=" * 100)
    print("CALCULATING AREA-SPECIFIC TRAIN THRESHOLDS")
    print("=" * 100)

    train = df.loc[
        df["dataset_split"] == "train"
    ].copy()

    thresholds = {}

    for study_area in sorted(
        train["study_area"].unique()
    ):

        values = train.loc[
            train["study_area"] == study_area,
            TARGET_COLUMN,
        ].dropna()

        q90_raw = float(
            values.quantile(0.90)
        )

        # HIGH must use an integer number of maritime events.
        # ceil guarantees that the threshold is not below the
        # empirical 90th percentile.

        high_threshold = max(
            2,
            int(np.ceil(q90_raw)),
        )

        thresholds[
            study_area
        ] = {
            "q90_raw": q90_raw,
            "high_threshold": high_threshold,
        }

        print()
        print(study_area)
        print(
            f"  train rows      = {len(values):,}"
        )
        print(
            f"  mean events     = {values.mean():.3f}"
        )
        print(
            f"  q90 raw         = {q90_raw:.3f}"
        )
        print(
            f"  HIGH threshold  = {high_threshold}+"
        )

    return thresholds


# ======================================================================================
# TARGET CLASS
# ======================================================================================

def assign_traffic_level(
    df,
    thresholds,
):

    df = df.copy()

    def classify(row):

        value = int(
            row[TARGET_COLUMN]
        )

        study_area = row[
            "study_area"
        ]

        high_threshold = (
            thresholds[
                study_area
            ][
                "high_threshold"
            ]
        )

        if value == 0:
            return "LOW"

        if value >= high_threshold:
            return "HIGH"

        return "MEDIUM"

    df[
        "traffic_level"
    ] = df.apply(
        classify,
        axis=1,
    )

    class_mapping = {
        "LOW": 0,
        "MEDIUM": 1,
        "HIGH": 2,
    }

    df[
        "traffic_level_numeric"
    ] = (
        df[
            "traffic_level"
        ]
        .map(
            class_mapping
        )
        .astype(int)
    )

    return df


# ======================================================================================
# VALIDATION
# ======================================================================================

def validate_dataset(df):

    print()
    print("=" * 100)
    print("DATASET VALIDATION")
    print("=" * 100)

    feature_columns = (
        NUMERIC_FEATURES
        + CATEGORICAL_FEATURES
    )

    print(
        f"Dataset shape: {df.shape}"
    )

    print(
        f"Numeric features: "
        f"{len(NUMERIC_FEATURES)}"
    )

    print(
        f"Categorical features: "
        f"{len(CATEGORICAL_FEATURES)}"
    )

    print(
        f"Total model inputs before encoding: "
        f"{len(feature_columns)}"
    )

    missing_columns = [
        column
        for column in feature_columns
        if column not in df.columns
    ]

    print(
        f"Missing feature columns: "
        f"{missing_columns}"
    )

    if missing_columns:
        raise RuntimeError(
            "Missing required model features."
        )

    numeric_values = (
        df[
            NUMERIC_FEATURES
        ]
        .to_numpy(
            dtype=float
        )
    )

    nan_count = int(
        np.isnan(
            numeric_values
        ).sum()
    )

    inf_count = int(
        np.isinf(
            numeric_values
        ).sum()
    )

    print(
        f"NaN values in numeric features: "
        f"{nan_count}"
    )

    print(
        f"Inf values in numeric features: "
        f"{inf_count}"
    )

    if nan_count > 0:
        raise RuntimeError(
            "NaN found in final numeric features."
        )

    if inf_count > 0:
        raise RuntimeError(
            "Infinite value found in final numeric features."
        )


# ======================================================================================
# REPORT
# ======================================================================================

def print_summary(
    df,
    thresholds,
):

    print()
    print("=" * 100)
    print("FINAL MULTI-AREA ML DATASET")
    print("=" * 100)

    print(
        f"Rows: {len(df):,}"
    )

    print()
    print("ROWS BY SPLIT")
    print("-" * 70)

    print(
        df[
            "dataset_split"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("ROWS BY STUDY AREA / SPLIT")
    print("-" * 70)

    print(
        pd.crosstab(
            df[
                "study_area"
            ],
            df[
                "dataset_split"
            ],
        ).to_string()
    )

    print()
    print("TRAFFIC CLASS DISTRIBUTION")
    print("-" * 70)

    print(
        pd.crosstab(
            df[
                "dataset_split"
            ],
            df[
                "traffic_level"
            ],
        ).to_string()
    )

    print()
    print("TRAFFIC CLASS DISTRIBUTION BY AREA")
    print("-" * 70)

    table = pd.crosstab(
        [
            df[
                "study_area"
            ],
            df[
                "dataset_split"
            ],
        ],
        df[
            "traffic_level"
        ],
    )

    print(
        table.to_string()
    )

    print()
    print("AREA THRESHOLDS")
    print("-" * 70)

    for area, values in thresholds.items():

        print(
            f"{area:<15} "
            f"q90={values['q90_raw']:.3f} | "
            f"HIGH={values['high_threshold']}+"
        )


# ======================================================================================
# METADATA
# ======================================================================================

def save_metadata(
    df,
    thresholds,
):

    metadata = {
        "dataset_name":
            "OceanEye Multi-Area ML V2",

        "study_areas":
            sorted(
                df[
                    "study_area"
                ]
                .unique()
                .tolist()
            ),

        "temporal_split": {
            "train":
                "2020-01-01 through 2024-12-31",

            "validation":
                "2025-01-01 through 2025-09-30",

            "test":
                "2025-10-01 through 2025-12-31",
        },

        "prediction_horizon_hours":
            1,

        "target_source":
            TARGET_COLUMN,

        "traffic_level_definition": {
            "LOW":
                "0 events in next hour",

            "MEDIUM":
                "1 or more events but below area-specific HIGH threshold",

            "HIGH":
                "at or above area-specific TRAIN q90 threshold",
        },

        "thresholds":
            thresholds,

        "numeric_features":
            NUMERIC_FEATURES,

        "categorical_features":
            CATEGORICAL_FEATURES,

        "class_mapping": {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
        },

        "rows":
            len(df),

        "rows_by_split":
            {
                key: int(value)
                for key, value in (
                    df[
                        "dataset_split"
                    ]
                    .value_counts()
                    .to_dict()
                    .items()
                )
            },
    }

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )


# ======================================================================================
# MAIN
# ======================================================================================

def main():

    df = load_dataset()

    df = assign_temporal_split(
        df
    )

    df = remove_boundary_rows(
        df
    )

    thresholds = calculate_area_thresholds(
        df
    )

    df = assign_traffic_level(
        df,
        thresholds,
    )

    validate_dataset(
        df
    )

    df = (
        df
        .sort_values(
            [
                "timestamp_utc",
                "study_area",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    save_metadata(
        df,
        thresholds,
    )

    print_summary(
        df,
        thresholds,
    )

    print()
    print("=" * 100)
    print("OUTPUT FILES")
    print("=" * 100)

    print(
        OUTPUT_FILE
    )

    print(
        METADATA_FILE
    )


if __name__ == "__main__":
    main()