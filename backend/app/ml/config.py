from pathlib import Path


# ======================================================================================
# PROJECT PATHS
# ======================================================================================

# config.py:
#
# OceanEye/
# └── backend/
#     └── app/
#         └── ml/
#             └── config.py
#
# parents[3] -> OceanEye/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

ML_ROOT = PROJECT_ROOT / "ml"

MODEL_DIR = ML_ROOT / "models"

MODEL_FILE = (
    MODEL_DIR
    / "traffic_classifier.joblib"
)

MODEL_METADATA_FILE = (
    MODEL_DIR
    / "traffic_classifier_metadata.json"
)


# ======================================================================================
# MODEL INPUT FEATURES
# ======================================================================================

FEATURE_COLUMNS = [
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
]


# ======================================================================================
# CLASSES
# ======================================================================================

CLASS_MAPPING = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
}

INVERSE_CLASS_MAPPING = {
    0: "LOW",
    1: "MEDIUM",
    2: "HIGH",
}


# ======================================================================================
# CURRENT ML DESIGN
# ======================================================================================

STUDY_AREA = "Ålesund municipality, Norway"

PREDICTION_HORIZON_HOURS = 1

TARGET_DESCRIPTION = (
    "Maritime traffic level in Ålesund during the next hour"
)