from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from xgboost import XGBClassifier


# ======================================================================================
# PATHS
# ======================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FEATURES_DIR = (
    BASE_DIR
    / "data"
    / "features"
)

MODELS_DIR = (
    BASE_DIR
    / "models"
)

DATASET_FILE = (
    FEATURES_DIR
    / "multi_area_ml_dataset.csv"
)

METADATA_FILE = (
    FEATURES_DIR
    / "multi_area_ml_metadata.json"
)

OUTPUT_MODEL_FILE = (
    MODELS_DIR
    / "traffic_classifier_multi_area_tuned.joblib"
)


# ======================================================================================
# CONFIG
# ======================================================================================

TARGET_COLUMN = (
    "traffic_level_numeric"
)

RANDOM_STATE = 42


XGB_08_PARAMS = {
    "n_estimators": 400,
    "learning_rate": 0.04,
    "max_depth": 8,
    "min_child_weight": 5,
    "subsample": 0.9,
    "colsample_bytree": 0.85,
}


# ======================================================================================
# MAIN
# ======================================================================================

def main():

    print("=" * 90)
    print("OCEANEYE PRODUCTION MODEL RECOVERY")
    print("=" * 90)

    # ----------------------------------------------------------------------------------
    # Load dataset
    # ----------------------------------------------------------------------------------

    print()
    print("Loading dataset...")

    df = pd.read_csv(
        DATASET_FILE,
        low_memory=False,
    )

    # ----------------------------------------------------------------------------------
    # Load metadata
    # ----------------------------------------------------------------------------------

    with open(
        METADATA_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(
            file
        )

    numeric_features = (
        metadata[
            "numeric_features"
        ]
    )

    categorical_features = (
        metadata[
            "categorical_features"
        ]
    )

    feature_columns = (
        numeric_features
        +
        categorical_features
    )

    # ----------------------------------------------------------------------------------
    # Use the exact original TRAIN split
    # ----------------------------------------------------------------------------------

    train = (
        df.loc[
            df["dataset_split"]
            == "train"
        ]
        .copy()
    )

    X_train = (
        train[
            feature_columns
        ]
    )

    y_train = (
        train[
            TARGET_COLUMN
        ]
    )

    print(
        f"Train rows: {len(train):,}"
    )

    print(
        f"Features:   {len(feature_columns)}"
    )

    # ----------------------------------------------------------------------------------
    # Preprocessor
    # ----------------------------------------------------------------------------------

    preprocessor = (
        ColumnTransformer(
            transformers=[
                (
                    "numeric",
                    "passthrough",
                    numeric_features,
                ),
                (
                    "categorical",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                    categorical_features,
                ),
            ],
            remainder="drop",
        )
    )

    # ----------------------------------------------------------------------------------
    # Exact XGB_08 configuration
    # ----------------------------------------------------------------------------------

    estimator = (
        XGBClassifier(
            **XGB_08_PARAMS,
            objective="multi:softprob",
            eval_metric="mlogloss",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )
    )

    model = (
        Pipeline(
            steps=[
                (
                    "preprocessor",
                    preprocessor,
                ),
                (
                    "model",
                    estimator,
                ),
            ]
        )
    )

    # ----------------------------------------------------------------------------------
    # Train
    # ----------------------------------------------------------------------------------

    print()
    print("Training XGB_08...")

    model.fit(
        X_train,
        y_train,
    )

    # ----------------------------------------------------------------------------------
    # Save
    # ----------------------------------------------------------------------------------

    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        OUTPUT_MODEL_FILE,
    )

    print()
    print("=" * 90)
    print("MODEL RECOVERED")
    print("=" * 90)

    print(
        f"Saved to:"
    )

    print(
        OUTPUT_MODEL_FILE
    )


if __name__ == "__main__":
    main()