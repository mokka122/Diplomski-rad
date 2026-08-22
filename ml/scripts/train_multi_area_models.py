from pathlib import Path
import json
import time
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
)

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier


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

VALIDATION_RESULTS_FILE = (
    RESULTS_DIR
    / "multi_area_validation_results.csv"
)

DETAILS_FILE = (
    RESULTS_DIR
    / "multi_area_validation_details.json"
)

BEST_MODEL_FILE = (
    MODELS_DIR
    / "traffic_classifier_multi_area.joblib"
)

BEST_MODEL_METADATA_FILE = (
    MODELS_DIR
    / "traffic_classifier_multi_area_metadata.json"
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

    print(
        f"Numeric features: "
        f"{len(numeric_features)}"
    )

    print(
        f"Categorical features: "
        f"{len(categorical_features)}"
    )

    return (
        df,
        metadata,
        numeric_features,
        categorical_features,
        X_train,
        y_train,
        X_validation,
        y_validation,
        X_test,
        y_test,
    )


# ======================================================================================
# PREPROCESSORS
# ======================================================================================

def build_tree_preprocessor(
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


def build_scaled_preprocessor(
    numeric_features,
    categorical_features,
):

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                StandardScaler(),
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
# MODELS
# ======================================================================================

def build_models(
    numeric_features,
    categorical_features,
):

    tree_preprocessor = (
        build_tree_preprocessor(
            numeric_features,
            categorical_features,
        )
    )

    scaled_preprocessor = (
        build_scaled_preprocessor(
            numeric_features,
            categorical_features,
        )
    )

    models = {
        "DummyClassifier": Pipeline(
            steps=[
                (
                    "preprocessor",
                    tree_preprocessor,
                ),
                (
                    "model",
                    DummyClassifier(
                        strategy="most_frequent",
                    ),
                ),
            ]
        ),

        "LogisticRegression": Pipeline(
            steps=[
                (
                    "preprocessor",
                    scaled_preprocessor,
                ),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),

        "DecisionTree": Pipeline(
            steps=[
                (
                    "preprocessor",
                    tree_preprocessor,
                ),
                (
                    "model",
                    DecisionTreeClassifier(
                        max_depth=16,
                        min_samples_leaf=10,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),

        "RandomForest": Pipeline(
            steps=[
                (
                    "preprocessor",
                    tree_preprocessor,
                ),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=None,
                        min_samples_leaf=2,
                        max_features="sqrt",
                        class_weight="balanced_subsample",
                        n_jobs=-1,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),

        "ExtraTrees": Pipeline(
            steps=[
                (
                    "preprocessor",
                    tree_preprocessor,
                ),
                (
                    "model",
                    ExtraTreesClassifier(
                        n_estimators=300,
                        max_depth=None,
                        min_samples_leaf=2,
                        max_features="sqrt",
                        class_weight="balanced",
                        n_jobs=-1,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),

        "HistGradientBoosting": Pipeline(
            steps=[
                (
                    "preprocessor",
                    tree_preprocessor,
                ),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=0.08,
                        max_iter=250,
                        max_leaf_nodes=31,
                        l2_regularization=1.0,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),

        "XGBoost": Pipeline(
            steps=[
                (
                    "preprocessor",
                    tree_preprocessor,
                ),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=350,
                        learning_rate=0.05,
                        max_depth=7,
                        min_child_weight=3,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        objective="multi:softprob",
                        eval_metric="mlogloss",
                        n_jobs=-1,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),

        "LightGBM": Pipeline(
            steps=[
                (
                    "preprocessor",
                    tree_preprocessor,
                ),
                (
                    "model",
                    LGBMClassifier(
                        n_estimators=350,
                        learning_rate=0.05,
                        num_leaves=31,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        class_weight="balanced",
                        n_jobs=-1,
                        random_state=RANDOM_STATE,
                        verbosity=-1,
                    ),
                ),
            ]
        ),

        "CatBoost": Pipeline(
            steps=[
                (
                    "preprocessor",
                    tree_preprocessor,
                ),
                (
                    "model",
                    CatBoostClassifier(
                        iterations=350,
                        learning_rate=0.05,
                        depth=8,
                        loss_function="MultiClass",
                        random_seed=RANDOM_STATE,
                        verbose=False,
                        allow_writing_files=False,
                    ),
                ),
            ]
        ),
    }

    return models


# ======================================================================================
# EVALUATION
# ======================================================================================

def calculate_metrics(
    y_true,
    y_pred,
):

    return {
        "accuracy":
            float(
                accuracy_score(
                    y_true,
                    y_pred,
                )
            ),

        "macro_precision":
            float(
                precision_score(
                    y_true,
                    y_pred,
                    average="macro",
                    zero_division=0,
                )
            ),

        "macro_recall":
            float(
                recall_score(
                    y_true,
                    y_pred,
                    average="macro",
                    zero_division=0,
                )
            ),

        "macro_f1":
            float(
                f1_score(
                    y_true,
                    y_pred,
                    average="macro",
                    zero_division=0,
                )
            ),

        "weighted_f1":
            float(
                f1_score(
                    y_true,
                    y_pred,
                    average="weighted",
                    zero_division=0,
                )
            ),
    }


def evaluate_model(
    name,
    model,
    X,
    y,
):

    predictions = model.predict(
        X
    )

    metrics = calculate_metrics(
        y,
        predictions,
    )

    report = classification_report(
        y,
        predictions,
        labels=[0, 1, 2],
        target_names=CLASS_NAMES,
        zero_division=0,
        output_dict=True,
    )

    matrix = confusion_matrix(
        y,
        predictions,
        labels=[0, 1, 2],
    )

    print()
    print("-" * 100)
    print(name)
    print("-" * 100)

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

    print()
    print("Confusion matrix:")

    print(
        matrix
    )

    return (
        predictions,
        metrics,
        report,
        matrix,
    )


# ======================================================================================
# PER-AREA VALIDATION
# ======================================================================================

def calculate_per_area_metrics(
    validation_df,
    predictions,
):

    result = {}

    validation_df = (
        validation_df
        .copy()
        .reset_index(drop=True)
    )

    validation_df[
        "prediction"
    ] = predictions

    for area in sorted(
        validation_df[
            "study_area"
        ].unique()
    ):

        area_data = validation_df.loc[
            validation_df[
                "study_area"
            ]
            == area
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
            area
        ] = metrics

    return result


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
        X_train,
        y_train,
        X_validation,
        y_validation,
        X_test,
        y_test,
    ) = load_data()

    models = build_models(
        numeric_features,
        categorical_features,
    )

    results = []

    details = {}

    trained_models = {}

    validation_df = df.loc[
        df[
            "dataset_split"
        ]
        == "validation"
    ].copy()

    print()
    print("=" * 100)
    print("TRAINING MULTI-AREA MODELS")
    print("=" * 100)

    for name, model in models.items():

        print()
        print("=" * 100)
        print(
            f"TRAINING: {name}"
        )
        print("=" * 100)

        start = time.perf_counter()

        model.fit(
            X_train,
            y_train,
        )

        training_seconds = (
            time.perf_counter()
            - start
        )

        print(
            f"Training time: "
            f"{training_seconds:.2f} s"
        )

        (
            validation_predictions,
            validation_metrics,
            validation_report,
            validation_matrix,
        ) = evaluate_model(
            name=name,
            model=model,
            X=X_validation,
            y=y_validation,
        )

        per_area_metrics = (
            calculate_per_area_metrics(
                validation_df,
                validation_predictions,
            )
        )

        row = {
            "model": name,
            "training_seconds":
                training_seconds,
            **validation_metrics,
        }

        results.append(
            row
        )

        details[
            name
        ] = {
            "training_seconds":
                training_seconds,

            "validation_metrics":
                validation_metrics,

            "classification_report":
                validation_report,

            "confusion_matrix":
                validation_matrix.tolist(),

            "per_area_validation":
                per_area_metrics,
        }

        trained_models[
            name
        ] = model

    # ----------------------------------------------------------------------------------
    # Ranking
    # ----------------------------------------------------------------------------------

    results_df = pd.DataFrame(
        results
    )

    results_df = (
        results_df
        .sort_values(
            "macro_f1",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )

    results_df.to_csv(
        VALIDATION_RESULTS_FILE,
        index=False,
        encoding="utf-8",
    )

    with open(
        DETAILS_FILE,
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
    print("VALIDATION RANKING")
    print("=" * 100)

    print(
        results_df[
            [
                "model",
                "macro_f1",
                "accuracy",
                "macro_precision",
                "macro_recall",
                "weighted_f1",
                "training_seconds",
            ]
        ].to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------
    # Select best model using validation Macro F1 only
    # ----------------------------------------------------------------------------------

    best_model_name = (
        results_df
        .iloc[0][
            "model"
        ]
    )

    best_model = (
        trained_models[
            best_model_name
        ]
    )

    print()
    print("=" * 100)
    print(
        f"BEST VALIDATION MODEL: "
        f"{best_model_name}"
    )
    print("=" * 100)

    # ----------------------------------------------------------------------------------
    # Final untouched test evaluation
    # ----------------------------------------------------------------------------------

    (
        test_predictions,
        test_metrics,
        test_report,
        test_matrix,
    ) = evaluate_model(
        name=(
            f"{best_model_name} - FINAL TEST"
        ),
        model=best_model,
        X=X_test,
        y=y_test,
    )

    test_df = df.loc[
        df[
            "dataset_split"
        ]
        == "test"
    ].copy()

    per_area_test = (
        calculate_per_area_metrics(
            test_df,
            test_predictions,
        )
    )

    # ----------------------------------------------------------------------------------
    # Save model
    # ----------------------------------------------------------------------------------

    joblib.dump(
        best_model,
        BEST_MODEL_FILE,
    )

    final_metadata = {
        "model_name":
            best_model_name,

        "selection_metric":
            "validation_macro_f1",

        "validation_metrics":
            details[
                best_model_name
            ][
                "validation_metrics"
            ],

        "test_metrics":
            test_metrics,

        "test_classification_report":
            test_report,

        "test_confusion_matrix":
            test_matrix.tolist(),

        "per_area_validation":
            details[
                best_model_name
            ][
                "per_area_validation"
            ],

        "per_area_test":
            per_area_test,

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

        "prediction_horizon_hours":
            metadata[
                "prediction_horizon_hours"
            ],
    }

    with open(
        BEST_MODEL_METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            final_metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 100)
    print("SAVED ARTIFACTS")
    print("=" * 100)

    print(
        VALIDATION_RESULTS_FILE
    )

    print(
        DETAILS_FILE
    )

    print(
        BEST_MODEL_FILE
    )

    print(
        BEST_MODEL_METADATA_FILE
    )


if __name__ == "__main__":
    main()