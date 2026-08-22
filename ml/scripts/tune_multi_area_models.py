from pathlib import Path
import json
import time
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from sklearn.ensemble import (
    RandomForestClassifier,
    HistGradientBoostingClassifier,
)

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

from xgboost import XGBClassifier


warnings.filterwarnings("ignore")


# ======================================================================================
# PATHS
# ======================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FEATURES_DIR = BASE_DIR / "data" / "features"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"

DATASET_FILE = (
    FEATURES_DIR
    / "multi_area_ml_dataset.csv"
)

METADATA_FILE = (
    FEATURES_DIR
    / "multi_area_ml_metadata.json"
)

TUNING_RESULTS_FILE = (
    RESULTS_DIR
    / "multi_area_tuning_results.csv"
)

TUNING_DETAILS_FILE = (
    RESULTS_DIR
    / "multi_area_tuning_details.json"
)

BEST_MODEL_FILE = (
    MODELS_DIR
    / "traffic_classifier_multi_area_tuned.joblib"
)

BEST_METADATA_FILE = (
    MODELS_DIR
    / "traffic_classifier_multi_area_tuned_metadata.json"
)


# ======================================================================================
# CONFIG
# ======================================================================================

TARGET_COLUMN = "traffic_level_numeric"

CLASS_NAMES = [
    "LOW",
    "MEDIUM",
    "HIGH",
]

RANDOM_STATE = 42


# ======================================================================================
# METRICS
# ======================================================================================

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


# ======================================================================================
# LOAD DATA
# ======================================================================================

def load_data():

    print("=" * 100)
    print("LOADING MULTI-AREA ML DATASET")
    print("=" * 100)

    df = pd.read_csv(
        DATASET_FILE,
        low_memory=False,
    )

    with open(
        METADATA_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        metadata = json.load(file)

    numeric_features = metadata[
        "numeric_features"
    ]

    categorical_features = metadata[
        "categorical_features"
    ]

    feature_columns = (
        numeric_features
        + categorical_features
    )

    train = df.loc[
        df["dataset_split"] == "train"
    ].copy()

    validation = df.loc[
        df["dataset_split"] == "validation"
    ].copy()

    test = df.loc[
        df["dataset_split"] == "test"
    ].copy()

    X_train = train[
        feature_columns
    ]

    y_train = train[
        TARGET_COLUMN
    ]

    X_validation = validation[
        feature_columns
    ]

    y_validation = validation[
        TARGET_COLUMN
    ]

    X_test = test[
        feature_columns
    ]

    y_test = test[
        TARGET_COLUMN
    ]

    print(
        f"Train rows:      {len(train):,}"
    )

    print(
        f"Validation rows: {len(validation):,}"
    )

    print(
        f"Test rows:       {len(test):,}"
    )

    return (
        df,
        metadata,
        numeric_features,
        categorical_features,
        train,
        validation,
        test,
        X_train,
        y_train,
        X_validation,
        y_validation,
        X_test,
        y_test,
    )


# ======================================================================================
# PREPROCESSOR
# ======================================================================================

def build_preprocessor(
    numeric_features,
    categorical_features,
):

    return ColumnTransformer(
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


# ======================================================================================
# PARAMETER CONFIGURATIONS
# ======================================================================================

def get_candidates():

    candidates = []

    # ----------------------------------------------------------------------------------
    # XGBOOST
    # ----------------------------------------------------------------------------------

    xgb_configs = [
        {
            "n_estimators": 300,
            "learning_rate": 0.03,
            "max_depth": 5,
            "min_child_weight": 1,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
        },
        {
            "n_estimators": 400,
            "learning_rate": 0.03,
            "max_depth": 7,
            "min_child_weight": 1,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
        },
        {
            "n_estimators": 500,
            "learning_rate": 0.03,
            "max_depth": 7,
            "min_child_weight": 3,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
        },
        {
            "n_estimators": 350,
            "learning_rate": 0.05,
            "max_depth": 5,
            "min_child_weight": 3,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
        },
        {
            "n_estimators": 450,
            "learning_rate": 0.05,
            "max_depth": 7,
            "min_child_weight": 3,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
        },
        {
            "n_estimators": 350,
            "learning_rate": 0.05,
            "max_depth": 9,
            "min_child_weight": 3,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
        },
        {
            "n_estimators": 300,
            "learning_rate": 0.07,
            "max_depth": 6,
            "min_child_weight": 3,
            "subsample": 0.85,
            "colsample_bytree": 0.9,
        },
        {
            "n_estimators": 400,
            "learning_rate": 0.04,
            "max_depth": 8,
            "min_child_weight": 5,
            "subsample": 0.9,
            "colsample_bytree": 0.85,
        },
    ]

    for index, config in enumerate(
        xgb_configs,
        start=1,
    ):
        candidates.append(
            {
                "model_family": "XGBoost",
                "candidate_id": f"XGB_{index:02d}",
                "params": config,
            }
        )

    # ----------------------------------------------------------------------------------
    # HIST GRADIENT BOOSTING
    # ----------------------------------------------------------------------------------

    hgb_configs = [
        {
            "learning_rate": 0.05,
            "max_iter": 250,
            "max_leaf_nodes": 31,
            "min_samples_leaf": 20,
            "l2_regularization": 1.0,
        },
        {
            "learning_rate": 0.05,
            "max_iter": 350,
            "max_leaf_nodes": 31,
            "min_samples_leaf": 20,
            "l2_regularization": 1.0,
        },
        {
            "learning_rate": 0.05,
            "max_iter": 350,
            "max_leaf_nodes": 63,
            "min_samples_leaf": 20,
            "l2_regularization": 1.0,
        },
        {
            "learning_rate": 0.08,
            "max_iter": 250,
            "max_leaf_nodes": 31,
            "min_samples_leaf": 20,
            "l2_regularization": 1.0,
        },
        {
            "learning_rate": 0.08,
            "max_iter": 300,
            "max_leaf_nodes": 63,
            "min_samples_leaf": 20,
            "l2_regularization": 1.0,
        },
        {
            "learning_rate": 0.04,
            "max_iter": 400,
            "max_leaf_nodes": 63,
            "min_samples_leaf": 30,
            "l2_regularization": 2.0,
        },
        {
            "learning_rate": 0.06,
            "max_iter": 300,
            "max_leaf_nodes": 47,
            "min_samples_leaf": 30,
            "l2_regularization": 5.0,
        },
        {
            "learning_rate": 0.04,
            "max_iter": 450,
            "max_leaf_nodes": 31,
            "min_samples_leaf": 40,
            "l2_regularization": 5.0,
        },
    ]

    for index, config in enumerate(
        hgb_configs,
        start=1,
    ):
        candidates.append(
            {
                "model_family":
                    "HistGradientBoosting",

                "candidate_id":
                    f"HGB_{index:02d}",

                "params":
                    config,
            }
        )

    # ----------------------------------------------------------------------------------
    # RANDOM FOREST
    # ----------------------------------------------------------------------------------

    rf_configs = [
        {
            "n_estimators": 400,
            "max_depth": None,
            "min_samples_leaf": 1,
            "max_features": "sqrt",
        },
        {
            "n_estimators": 400,
            "max_depth": None,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
        },
        {
            "n_estimators": 500,
            "max_depth": 24,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
        },
        {
            "n_estimators": 500,
            "max_depth": 32,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
        },
        {
            "n_estimators": 500,
            "max_depth": None,
            "min_samples_leaf": 4,
            "max_features": "sqrt",
        },
        {
            "n_estimators": 400,
            "max_depth": None,
            "min_samples_leaf": 2,
            "max_features": 0.5,
        },
    ]

    for index, config in enumerate(
        rf_configs,
        start=1,
    ):
        candidates.append(
            {
                "model_family":
                    "RandomForest",

                "candidate_id":
                    f"RF_{index:02d}",

                "params":
                    config,
            }
        )

    return candidates


# ======================================================================================
# MODEL BUILDER
# ======================================================================================

def build_model(
    candidate,
    numeric_features,
    categorical_features,
):

    preprocessor = build_preprocessor(
        numeric_features,
        categorical_features,
    )

    family = candidate[
        "model_family"
    ]

    params = candidate[
        "params"
    ]

    if family == "XGBoost":

        estimator = XGBClassifier(
            **params,
            objective="multi:softprob",
            eval_metric="mlogloss",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )

    elif family == "HistGradientBoosting":

        estimator = HistGradientBoostingClassifier(
            **params,
            random_state=RANDOM_STATE,
        )

    elif family == "RandomForest":

        estimator = RandomForestClassifier(
            **params,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )

    else:

        raise ValueError(
            f"Unknown model family: {family}"
        )

    return Pipeline(
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


# ======================================================================================
# PER AREA METRICS
# ======================================================================================

def calculate_per_area_metrics(
    data,
    predictions,
):

    temp = (
        data
        .copy()
        .reset_index(drop=True)
    )

    temp[
        "prediction"
    ] = predictions

    result = {}

    area_macro_f1_values = []

    for study_area in sorted(
        temp[
            "study_area"
        ].unique()
    ):

        area_data = temp.loc[
            temp[
                "study_area"
            ]
            == study_area
        ]

        metrics = calculate_metrics(
            area_data[
                TARGET_COLUMN
            ],
            area_data[
                "prediction"
            ],
        )

        result[
            study_area
        ] = metrics

        area_macro_f1_values.append(
            metrics[
                "macro_f1"
            ]
        )

    mean_area_macro_f1 = float(
        np.mean(
            area_macro_f1_values
        )
    )

    return (
        result,
        mean_area_macro_f1,
    )


# ======================================================================================
# MAIN
# ======================================================================================

def main():

    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        df,
        metadata,
        numeric_features,
        categorical_features,
        train,
        validation,
        test,
        X_train,
        y_train,
        X_validation,
        y_validation,
        X_test,
        y_test,
    ) = load_data()

    candidates = get_candidates()

    print()
    print(
        f"Total tuning candidates: "
        f"{len(candidates)}"
    )

    results = []
    details = {}

    best_model = None
    best_candidate = None
    best_macro_f1 = -1.0

    # ==================================================================================
    # VALIDATION TUNING
    # ==================================================================================

    for number, candidate in enumerate(
        candidates,
        start=1,
    ):

        family = candidate[
            "model_family"
        ]

        candidate_id = candidate[
            "candidate_id"
        ]

        params = candidate[
            "params"
        ]

        print()
        print("=" * 100)

        print(
            f"[{number}/{len(candidates)}] "
            f"{candidate_id} - {family}"
        )

        print(
            params
        )

        print("=" * 100)

        model = build_model(
            candidate,
            numeric_features,
            categorical_features,
        )

        start = time.perf_counter()

        model.fit(
            X_train,
            y_train,
        )

        training_seconds = (
            time.perf_counter()
            - start
        )

        predictions = model.predict(
            X_validation
        )

        metrics = calculate_metrics(
            y_validation,
            predictions,
        )

        (
            per_area,
            mean_area_macro_f1,
        ) = calculate_per_area_metrics(
            validation,
            predictions,
        )

        print(
            f"Training time: "
            f"{training_seconds:.2f} s"
        )

        print(
            f"Validation accuracy: "
            f"{metrics['accuracy']:.4f}"
        )

        print(
            f"Validation Macro F1: "
            f"{metrics['macro_f1']:.4f}"
        )

        print(
            f"Mean area Macro F1: "
            f"{mean_area_macro_f1:.4f}"
        )

        row = {
            "candidate_id":
                candidate_id,

            "model_family":
                family,

            "macro_f1":
                metrics[
                    "macro_f1"
                ],

            "mean_area_macro_f1":
                mean_area_macro_f1,

            "accuracy":
                metrics[
                    "accuracy"
                ],

            "macro_precision":
                metrics[
                    "macro_precision"
                ],

            "macro_recall":
                metrics[
                    "macro_recall"
                ],

            "weighted_f1":
                metrics[
                    "weighted_f1"
                ],

            "training_seconds":
                training_seconds,

            "parameters":
                json.dumps(
                    params,
                    ensure_ascii=False,
                ),
        }

        results.append(
            row
        )

        details[
            candidate_id
        ] = {
            "model_family":
                family,

            "parameters":
                params,

            "validation_metrics":
                metrics,

            "mean_area_macro_f1":
                mean_area_macro_f1,

            "per_area_validation":
                per_area,
        }

        # Primary model-selection criterion:
        # validation Macro F1

        if (
            metrics[
                "macro_f1"
            ]
            > best_macro_f1
        ):

            best_macro_f1 = metrics[
                "macro_f1"
            ]

            best_model = model

            best_candidate = candidate

    # ==================================================================================
    # RANKING
    # ==================================================================================

    results_df = pd.DataFrame(
        results
    )

    results_df = (
        results_df
        .sort_values(
            by=[
                "macro_f1",
                "mean_area_macro_f1",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .reset_index(
            drop=True
        )
    )

    results_df.to_csv(
        TUNING_RESULTS_FILE,
        index=False,
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print("TUNING RANKING")
    print("=" * 100)

    print(
        results_df[
            [
                "candidate_id",
                "model_family",
                "macro_f1",
                "mean_area_macro_f1",
                "accuracy",
                "macro_precision",
                "macro_recall",
                "weighted_f1",
                "training_seconds",
            ]
        ]
        .to_string(
            index=False
        )
    )

    # ==================================================================================
    # FINAL TEST - ONLY BEST VALIDATION CANDIDATE
    # ==================================================================================

    print()
    print("=" * 100)
    print("BEST TUNED CANDIDATE")
    print("=" * 100)

    print(
        best_candidate
    )

    print(
        f"Validation Macro F1: "
        f"{best_macro_f1:.4f}"
    )

    test_predictions = (
        best_model.predict(
            X_test
        )
    )

    test_metrics = calculate_metrics(
        y_test,
        test_predictions,
    )

    (
        per_area_test,
        mean_area_test_macro_f1,
    ) = calculate_per_area_metrics(
        test,
        test_predictions,
    )

    test_matrix = confusion_matrix(
        y_test,
        test_predictions,
        labels=[0, 1, 2],
    )

    test_report = classification_report(
        y_test,
        test_predictions,
        labels=[0, 1, 2],
        target_names=CLASS_NAMES,
        zero_division=0,
        output_dict=True,
    )

    print()
    print("=" * 100)
    print("FINAL TEST RESULT")
    print("=" * 100)

    print(
        f"Accuracy:        "
        f"{test_metrics['accuracy']:.4f}"
    )

    print(
        f"Macro Precision: "
        f"{test_metrics['macro_precision']:.4f}"
    )

    print(
        f"Macro Recall:    "
        f"{test_metrics['macro_recall']:.4f}"
    )

    print(
        f"Macro F1:        "
        f"{test_metrics['macro_f1']:.4f}"
    )

    print(
        f"Weighted F1:     "
        f"{test_metrics['weighted_f1']:.4f}"
    )

    print(
        f"Mean area Macro F1: "
        f"{mean_area_test_macro_f1:.4f}"
    )

    print()
    print("Confusion matrix:")

    print(
        test_matrix
    )

    print()
    print("PER-AREA TEST MACRO F1")
    print("-" * 70)

    for area, metrics in (
        per_area_test.items()
    ):

        print(
            f"{area:<15} "
            f"{metrics['macro_f1']:.4f}"
        )

    # ==================================================================================
    # SAVE FINAL MODEL
    # ==================================================================================

    joblib.dump(
        best_model,
        BEST_MODEL_FILE,
    )

    final_metadata = {
        "candidate_id":
            best_candidate[
                "candidate_id"
            ],

        "model_family":
            best_candidate[
                "model_family"
            ],

        "parameters":
            best_candidate[
                "params"
            ],

        "selection_metric":
            "validation_macro_f1",

        "validation_macro_f1":
            best_macro_f1,

        "test_metrics":
            test_metrics,

        "mean_area_test_macro_f1":
            mean_area_test_macro_f1,

        "per_area_test":
            per_area_test,

        "test_confusion_matrix":
            test_matrix.tolist(),

        "test_classification_report":
            test_report,

        "study_areas":
            metadata[
                "study_areas"
            ],

        "thresholds":
            metadata[
                "thresholds"
            ],

        "numeric_features":
            numeric_features,

        "categorical_features":
            categorical_features,

        "class_mapping":
            metadata[
                "class_mapping"
            ],
    }

    with open(
        BEST_METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            final_metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with open(
        TUNING_DETAILS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            details,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 100)
    print("SAVED ARTIFACTS")
    print("=" * 100)

    print(
        TUNING_RESULTS_FILE
    )

    print(
        TUNING_DETAILS_FILE
    )

    print(
        BEST_MODEL_FILE
    )

    print(
        BEST_METADATA_FILE
    )


if __name__ == "__main__":
    main()