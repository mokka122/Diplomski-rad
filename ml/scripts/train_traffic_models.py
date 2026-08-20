from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


# ==================================================================================================
# PATHS
# ==================================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FEATURES_DIR = BASE_DIR / "data" / "features"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"

DATASET_FILE = (
    FEATURES_DIR
    / "alesund_ml_dataset.csv"
)

METADATA_FILE = (
    FEATURES_DIR
    / "alesund_ml_metadata.json"
)

RESULTS_FILE = (
    RESULTS_DIR
    / "model_validation_results.csv"
)

DETAILS_FILE = (
    RESULTS_DIR
    / "model_validation_details.json"
)

BEST_MODEL_FILE = (
    MODELS_DIR
    / "traffic_classifier.joblib"
)

BEST_MODEL_METADATA_FILE = (
    MODELS_DIR
    / "traffic_classifier_metadata.json"
)


# ==================================================================================================
# TARGET
# ==================================================================================================

TARGET_COLUMN = "traffic_level"

TARGET_NUMERIC_COLUMN = "traffic_level_numeric"


CLASS_NAMES = [
    "LOW",
    "MEDIUM",
    "HIGH",
]

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


# ==================================================================================================
# FEATURES
# ==================================================================================================

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


# ==================================================================================================
# LOAD DATA
# ==================================================================================================

def load_dataset():
    print("=" * 100)
    print("OCEANEYE - TRAIN TRAFFIC CLASSIFICATION MODELS")
    print("=" * 100)

    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_FILE}"
        )

    dataframe = pd.read_csv(
        DATASET_FILE
    )

    print()
    print(
        f"Loaded rows: "
        f"{len(dataframe):,}"
    )

    print(
        f"Features: "
        f"{len(FEATURE_COLUMNS)}"
    )

    return dataframe


# ==================================================================================================
# SPLIT DATA
# ==================================================================================================

def prepare_splits(dataframe):
    train = dataframe.loc[
        dataframe["dataset_split"] == "train"
    ].copy()

    validation = dataframe.loc[
        dataframe["dataset_split"] == "validation"
    ].copy()

    test = dataframe.loc[
        dataframe["dataset_split"] == "test"
    ].copy()

    print()
    print("DATASET SPLITS")
    print("-" * 60)

    print(
        f"Train:      "
        f"{len(train):,}"
    )

    print(
        f"Validation: "
        f"{len(validation):,}"
    )

    print(
        f"Test:       "
        f"{len(test):,}"
    )

    x_train = train[
        FEATURE_COLUMNS
    ].copy()

    y_train = train[
        TARGET_NUMERIC_COLUMN
    ].astype(int)

    x_validation = validation[
        FEATURE_COLUMNS
    ].copy()

    y_validation = validation[
        TARGET_NUMERIC_COLUMN
    ].astype(int)

    x_test = test[
        FEATURE_COLUMNS
    ].copy()

    y_test = test[
        TARGET_NUMERIC_COLUMN
    ].astype(int)

    return (
        x_train,
        y_train,
        x_validation,
        y_validation,
        x_test,
        y_test,
    )


# ==================================================================================================
# MODELS
# ==================================================================================================

def build_models():
    """
    We intentionally include:
    - trivial baseline
    - linear model
    - simple decision tree
    - bagged tree ensemble
    - boosting model
    """

    models = {
        "DummyClassifier": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "classifier",
                    DummyClassifier(
                        strategy="most_frequent"
                    ),
                ),
            ]
        ),

        "LogisticRegression": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "scaler",
                    StandardScaler(),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=3000,
                        random_state=42,
                    ),
                ),
            ]
        ),

        "DecisionTree": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "classifier",
                    DecisionTreeClassifier(
                        max_depth=12,
                        min_samples_leaf=10,
                        random_state=42,
                    ),
                ),
            ]
        ),

        "RandomForest": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=18,
                        min_samples_leaf=3,
                        n_jobs=-1,
                        random_state=42,
                    ),
                ),
            ]
        ),

        "HistGradientBoosting": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "classifier",
                    HistGradientBoostingClassifier(
                        learning_rate=0.08,
                        max_iter=250,
                        max_leaf_nodes=31,
                        l2_regularization=0.1,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }

    return models


# ==================================================================================================
# METRICS
# ==================================================================================================

def calculate_metrics(
    y_true,
    y_pred,
):
    return {
        "accuracy": float(
            accuracy_score(
                y_true,
                y_pred,
            )
        ),

        "macro_precision": float(
            precision_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "macro_recall": float(
            recall_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "macro_f1": float(
            f1_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "weighted_f1": float(
            f1_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0,
            )
        ),
    }


def print_metrics(
    name,
    metrics,
):
    print()
    print(name)
    print("-" * 70)

    print(
        f"Accuracy:        "
        f"{metrics['accuracy']:.4f}"
    )

    print(
        f"Macro Precision: "
        f"{metrics['macro_precision']:.4f}"
    )

    print(
        f"Macro Recall:    "
        f"{metrics['macro_recall']:.4f}"
    )

    print(
        f"Macro F1:        "
        f"{metrics['macro_f1']:.4f}"
    )

    print(
        f"Weighted F1:     "
        f"{metrics['weighted_f1']:.4f}"
    )


# ==================================================================================================
# TRAIN + VALIDATE
# ==================================================================================================

def train_models(
    models,
    x_train,
    y_train,
    x_validation,
    y_validation,
):
    results = []
    details = {}
    trained_models = {}

    print()
    print("=" * 100)
    print("TRAINING + VALIDATION")
    print("=" * 100)

    for name, model in models.items():
        print()
        print("=" * 100)
        print(
            f"MODEL: {name}"
        )
        print("=" * 100)

        start_time = time.perf_counter()

        model.fit(
            x_train,
            y_train,
        )

        training_seconds = (
            time.perf_counter()
            -
            start_time
        )

        predictions = model.predict(
            x_validation
        )

        metrics = calculate_metrics(
            y_true=y_validation,
            y_pred=predictions,
        )

        print_metrics(
            name=name,
            metrics=metrics,
        )

        print(
            f"Training time:   "
            f"{training_seconds:.3f} s"
        )

        cm = confusion_matrix(
            y_validation,
            predictions,
            labels=[
                0,
                1,
                2,
            ],
        )

        report = classification_report(
            y_validation,
            predictions,
            labels=[
                0,
                1,
                2,
            ],
            target_names=CLASS_NAMES,
            zero_division=0,
            output_dict=True,
        )

        print()
        print("CONFUSION MATRIX")
        print("-" * 70)

        print(
            "Rows = actual"
        )

        print(
            "Columns = predicted"
        )

        print()

        print(cm)

        results.append(
            {
                "model": name,
                "accuracy": metrics[
                    "accuracy"
                ],
                "macro_precision": metrics[
                    "macro_precision"
                ],
                "macro_recall": metrics[
                    "macro_recall"
                ],
                "macro_f1": metrics[
                    "macro_f1"
                ],
                "weighted_f1": metrics[
                    "weighted_f1"
                ],
                "training_seconds":
                    training_seconds,
            }
        )

        details[name] = {
            "metrics": metrics,
            "training_seconds":
                training_seconds,

            "confusion_matrix":
                cm.tolist(),

            "classification_report":
                report,
        }

        trained_models[
            name
        ] = model

    results_dataframe = pd.DataFrame(
        results
    )

    results_dataframe = (
        results_dataframe
        .sort_values(
            by="macro_f1",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    return (
        results_dataframe,
        details,
        trained_models,
    )


# ==================================================================================================
# RESULT TABLE
# ==================================================================================================

def print_results_table(
    results_dataframe,
):
    print()
    print("=" * 100)
    print("VALIDATION MODEL RANKING")
    print("=" * 100)

    printable = (
        results_dataframe[
            [
                "model",
                "accuracy",
                "macro_f1",
                "weighted_f1",
                "training_seconds",
            ]
        ]
        .copy()
    )

    printable[
        "accuracy"
    ] = printable[
        "accuracy"
    ].round(4)

    printable[
        "macro_f1"
    ] = printable[
        "macro_f1"
    ].round(4)

    printable[
        "weighted_f1"
    ] = printable[
        "weighted_f1"
    ].round(4)

    printable[
        "training_seconds"
    ] = printable[
        "training_seconds"
    ].round(3)

    print()
    print(
        printable.to_string(
            index=False
        )
    )


# ==================================================================================================
# BEST MODEL
# ==================================================================================================

def select_best_model(
    results_dataframe,
    trained_models,
):
    """
    Macro F1 is the primary model-selection metric.

    This is important because validation/test class proportions
    differ from the training period and HIGH is less frequent.
    """

    best_name = (
        results_dataframe
        .iloc[0]["model"]
    )

    best_model = trained_models[
        best_name
    ]

    print()
    print("=" * 100)
    print("BEST VALIDATION MODEL")
    print("=" * 100)

    print(
        f"Selected model: "
        f"{best_name}"
    )

    print(
        "Selection metric: "
        "Macro F1"
    )

    return (
        best_name,
        best_model,
    )


# ==================================================================================================
# FINAL TEST EVALUATION
# ==================================================================================================

def evaluate_on_test(
    model_name,
    model,
    x_test,
    y_test,
):
    print()
    print("=" * 100)
    print("FINAL TEST EVALUATION")
    print("=" * 100)

    predictions = model.predict(
        x_test
    )

    metrics = calculate_metrics(
        y_true=y_test,
        y_pred=predictions,
    )

    print_metrics(
        name=model_name,
        metrics=metrics,
    )

    cm = confusion_matrix(
        y_test,
        predictions,
        labels=[
            0,
            1,
            2,
        ],
    )

    report = classification_report(
        y_test,
        predictions,
        labels=[
            0,
            1,
            2,
        ],
        target_names=CLASS_NAMES,
        zero_division=0,
        output_dict=True,
    )

    print()
    print("TEST CONFUSION MATRIX")
    print("-" * 70)

    print(
        "Rows = actual"
    )

    print(
        "Columns = predicted"
    )

    print()

    print(cm)

    return {
        "metrics": metrics,
        "confusion_matrix":
            cm.tolist(),
        "classification_report":
            report,
    }


# ==================================================================================================
# SAVE FINAL MODEL
# ==================================================================================================

def save_best_model(
    model_name,
    model,
    validation_results,
    test_results,
):
    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        BEST_MODEL_FILE,
    )

    metadata = {}

    if METADATA_FILE.exists():
        with open(
            METADATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            metadata = json.load(
                file
            )

    metadata.update(
        {
            "selected_model":
                model_name,

            "model_selection_metric":
                "macro_f1",

            "validation_results":
                validation_results,

            "test_results":
                test_results,

            "model_file":
                str(
                    BEST_MODEL_FILE
                ),

            "feature_columns":
                FEATURE_COLUMNS,

            "class_mapping":
                CLASS_MAPPING,

            "inverse_class_mapping":
                {
                    str(key): value
                    for key, value
                    in INVERSE_CLASS_MAPPING.items()
                },
        }
    )

    with open(
        BEST_MODEL_METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print()
    print("=" * 100)
    print("MODEL SAVED")
    print("=" * 100)

    print(
        f"Model:\n"
        f"{BEST_MODEL_FILE}"
    )

    print()

    print(
        f"Metadata:\n"
        f"{BEST_MODEL_METADATA_FILE}"
    )


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():
    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = load_dataset()

    (
        x_train,
        y_train,
        x_validation,
        y_validation,
        x_test,
        y_test,
    ) = prepare_splits(
        dataframe
    )

    models = build_models()

    (
        results_dataframe,
        details,
        trained_models,
    ) = train_models(
        models=models,
        x_train=x_train,
        y_train=y_train,
        x_validation=x_validation,
        y_validation=y_validation,
    )

    results_dataframe.to_csv(
        RESULTS_FILE,
        index=False,
        encoding="utf-8",
    )

    print_results_table(
        results_dataframe
    )

    (
        best_model_name,
        best_model,
    ) = select_best_model(
        results_dataframe=results_dataframe,
        trained_models=trained_models,
    )

    test_results = evaluate_on_test(
        model_name=best_model_name,
        model=best_model,
        x_test=x_test,
        y_test=y_test,
    )

    best_validation_row = (
        results_dataframe
        .loc[
            results_dataframe[
                "model"
            ]
            == best_model_name
        ]
        .iloc[0]
    )

    best_validation_results = {
        "accuracy": float(
            best_validation_row[
                "accuracy"
            ]
        ),

        "macro_precision": float(
            best_validation_row[
                "macro_precision"
            ]
        ),

        "macro_recall": float(
            best_validation_row[
                "macro_recall"
            ]
        ),

        "macro_f1": float(
            best_validation_row[
                "macro_f1"
            ]
        ),

        "weighted_f1": float(
            best_validation_row[
                "weighted_f1"
            ]
        ),

        "training_seconds": float(
            best_validation_row[
                "training_seconds"
            ]
        ),
    }

    details[
        "selected_model"
    ] = best_model_name

    details[
        "final_test"
    ] = test_results

    with open(
        DETAILS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            details,
            file,
            indent=4,
            ensure_ascii=False,
        )

    save_best_model(
        model_name=best_model_name,
        model=best_model,
        validation_results=
            best_validation_results,
        test_results=
            test_results,
    )

    print()
    print("=" * 100)
    print("OUTPUT FILES")
    print("=" * 100)

    print(
        f"Validation ranking:\n"
        f"{RESULTS_FILE}"
    )

    print()

    print(
        f"Detailed evaluation:\n"
        f"{DETAILS_FILE}"
    )


if __name__ == "__main__":
    main()