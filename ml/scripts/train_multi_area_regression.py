from pathlib import Path
import json
import time
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from xgboost import XGBRegressor


warnings.filterwarnings("ignore")


# ======================================================================================
# PATHS
# ======================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FEATURES_DIR = BASE_DIR / "data" / "features"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

DATASET_FILE = (
    FEATURES_DIR
    / "multi_area_ml_dataset.csv"
)

METADATA_FILE = (
    FEATURES_DIR
    / "multi_area_ml_metadata.json"
)

RESULTS_FILE = (
    RESULTS_DIR
    / "multi_area_regression_results.csv"
)

DETAILS_FILE = (
    RESULTS_DIR
    / "multi_area_regression_details.json"
)

BEST_MODEL_FILE = (
    MODELS_DIR
    / "traffic_regressor_multi_area.joblib"
)

BEST_METADATA_FILE = (
    MODELS_DIR
    / "traffic_regressor_multi_area_metadata.json"
)

FIGURE_FILE = (
    FIGURES_DIR
    / "09_regression_vs_classification_macro_f1.png"
)


# ======================================================================================
# CONFIG
# ======================================================================================

TARGET_COLUMN = "future_total_events_1h"

CLASS_COLUMN = "traffic_level_numeric"

RANDOM_STATE = 42


# ======================================================================================
# CANDIDATES
# ======================================================================================

CANDIDATES = [
    {
        "candidate_id": "REG_XGB_01",
        "n_estimators": 300,
        "learning_rate": 0.03,
        "max_depth": 5,
        "min_child_weight": 1,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        "candidate_id": "REG_XGB_02",
        "n_estimators": 400,
        "learning_rate": 0.03,
        "max_depth": 7,
        "min_child_weight": 1,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        "candidate_id": "REG_XGB_03",
        "n_estimators": 500,
        "learning_rate": 0.03,
        "max_depth": 7,
        "min_child_weight": 3,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        "candidate_id": "REG_XGB_04",
        "n_estimators": 350,
        "learning_rate": 0.05,
        "max_depth": 7,
        "min_child_weight": 3,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        "candidate_id": "REG_XGB_05",
        "n_estimators": 400,
        "learning_rate": 0.04,
        "max_depth": 8,
        "min_child_weight": 5,
        "subsample": 0.9,
        "colsample_bytree": 0.85,
    },
    {
        "candidate_id": "REG_XGB_06",
        "n_estimators": 350,
        "learning_rate": 0.05,
        "max_depth": 9,
        "min_child_weight": 3,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
]


# ======================================================================================
# METRICS
# ======================================================================================

def regression_metrics(y_true, y_pred):

    rmse = float(
        np.sqrt(
            mean_squared_error(
                y_true,
                y_pred,
            )
        )
    )

    return {
        "mae": float(
            mean_absolute_error(
                y_true,
                y_pred,
            )
        ),
        "rmse": rmse,
        "r2": float(
            r2_score(
                y_true,
                y_pred,
            )
        ),
    }


def classification_metrics(y_true, y_pred):

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
# LOAD
# ======================================================================================

def load_data():

    print("=" * 100)
    print("LOADING MULTI-AREA REGRESSION DATA")
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

    print(
        f"Train:      {len(train):,}"
    )

    print(
        f"Validation: {len(validation):,}"
    )

    print(
        f"Test:       {len(test):,}"
    )

    return (
        df,
        metadata,
        feature_columns,
        numeric_features,
        categorical_features,
        train,
        validation,
        test,
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
# MODEL
# ======================================================================================

def build_model(
    candidate,
    numeric_features,
    categorical_features,
):

    params = {
        key: value
        for key, value in candidate.items()
        if key != "candidate_id"
    }

    estimator = XGBRegressor(
        **params,
        objective="reg:squarederror",
        eval_metric="rmse",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )

    return Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    numeric_features,
                    categorical_features,
                ),
            ),
            (
                "model",
                estimator,
            ),
        ]
    )


# ======================================================================================
# REGRESSION → TRAFFIC LEVEL
# ======================================================================================

def regression_to_class(
    dataframe,
    predictions,
    thresholds,
):

    classes = []

    for (
        (_, row),
        predicted_value,
    ) in zip(
        dataframe.iterrows(),
        predictions,
    ):

        # Event counts cannot be negative.
        predicted_value = max(
            0.0,
            float(predicted_value),
        )

        area = row[
            "study_area"
        ]

        high_threshold = int(
            thresholds[
                area
            ][
                "high_threshold"
            ]
        )

        # Use a half-event boundary between
        # zero and one event.
        #
        # predicted < 0.5 -> LOW
        # predicted >= high threshold - 0.5 -> HIGH
        # otherwise MEDIUM

        if predicted_value < 0.5:
            traffic_class = 0

        elif (
            predicted_value
            >= high_threshold - 0.5
        ):
            traffic_class = 2

        else:
            traffic_class = 1

        classes.append(
            traffic_class
        )

    return np.array(
        classes,
        dtype=int,
    )


# ======================================================================================
# PER AREA
# ======================================================================================

def per_area_metrics(
    dataframe,
    regression_predictions,
    class_predictions,
):

    temp = (
        dataframe
        .copy()
        .reset_index(drop=True)
    )

    temp[
        "regression_prediction"
    ] = regression_predictions

    temp[
        "class_prediction"
    ] = class_predictions

    result = {}

    for area in sorted(
        temp[
            "study_area"
        ].unique()
    ):

        area_df = temp.loc[
            temp["study_area"] == area
        ]

        result[
            area
        ] = {
            "regression":
                regression_metrics(
                    area_df[
                        TARGET_COLUMN
                    ],
                    area_df[
                        "regression_prediction"
                    ],
                ),

            "classification":
                classification_metrics(
                    area_df[
                        CLASS_COLUMN
                    ],
                    area_df[
                        "class_prediction"
                    ],
                ),
        }

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

    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        df,
        metadata,
        feature_columns,
        numeric_features,
        categorical_features,
        train,
        validation,
        test,
    ) = load_data()

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

    thresholds = metadata[
        "thresholds"
    ]

    results = []
    details = {}

    best_model = None
    best_candidate = None
    best_validation_macro_f1 = -1

    print()
    print("=" * 100)
    print("V4 - MULTI-AREA REGRESSION")
    print("=" * 100)

    for (
        index,
        candidate,
    ) in enumerate(
        CANDIDATES,
        start=1,
    ):

        candidate_id = candidate[
            "candidate_id"
        ]

        print()
        print(
            f"[{index}/{len(CANDIDATES)}] "
            f"{candidate_id}"
        )

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

        validation_pred = (
            model.predict(
                X_validation
            )
        )

        validation_pred = np.clip(
            validation_pred,
            0,
            None,
        )

        reg_metrics = regression_metrics(
            y_validation,
            validation_pred,
        )

        class_pred = regression_to_class(
            validation,
            validation_pred,
            thresholds,
        )

        class_metrics = classification_metrics(
            validation[
                CLASS_COLUMN
            ],
            class_pred,
        )

        print(
            f"  time      = "
            f"{training_seconds:.2f} s"
        )

        print(
            f"  MAE       = "
            f"{reg_metrics['mae']:.4f}"
        )

        print(
            f"  RMSE      = "
            f"{reg_metrics['rmse']:.4f}"
        )

        print(
            f"  R2        = "
            f"{reg_metrics['r2']:.4f}"
        )

        print(
            f"  Macro F1  = "
            f"{class_metrics['macro_f1']:.4f}"
        )

        results.append(
            {
                "candidate_id":
                    candidate_id,

                "validation_mae":
                    reg_metrics[
                        "mae"
                    ],

                "validation_rmse":
                    reg_metrics[
                        "rmse"
                    ],

                "validation_r2":
                    reg_metrics[
                        "r2"
                    ],

                "validation_macro_f1":
                    class_metrics[
                        "macro_f1"
                    ],

                "validation_accuracy":
                    class_metrics[
                        "accuracy"
                    ],

                "training_seconds":
                    training_seconds,

                "parameters":
                    json.dumps(
                        {
                            key: value
                            for key, value
                            in candidate.items()
                            if key != "candidate_id"
                        }
                    ),
            }
        )

        details[
            candidate_id
        ] = {
            "parameters": {
                key: value
                for key, value
                in candidate.items()
                if key != "candidate_id"
            },

            "regression_metrics":
                reg_metrics,

            "classification_metrics":
                class_metrics,
        }

        # We choose according to the same final objective
        # used by the classifier experiment: Macro F1.

        if (
            class_metrics[
                "macro_f1"
            ]
            > best_validation_macro_f1
        ):

            best_validation_macro_f1 = (
                class_metrics[
                    "macro_f1"
                ]
            )

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
            "validation_macro_f1",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    results_df.to_csv(
        RESULTS_FILE,
        index=False,
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print("REGRESSION VALIDATION RANKING")
    print("=" * 100)

    print(
        results_df.to_string(
            index=False
        )
    )

    print()
    print("=" * 100)
    print("BEST REGRESSION CANDIDATE")
    print("=" * 100)

    print(
        best_candidate
    )

    print(
        f"Validation Macro F1: "
        f"{best_validation_macro_f1:.4f}"
    )

    # ==================================================================================
    # FINAL TEST
    # ==================================================================================

    test_reg_pred = (
        best_model.predict(
            X_test
        )
    )

    test_reg_pred = np.clip(
        test_reg_pred,
        0,
        None,
    )

    test_reg_metrics = (
        regression_metrics(
            y_test,
            test_reg_pred,
        )
    )

    test_class_pred = (
        regression_to_class(
            test,
            test_reg_pred,
            thresholds,
        )
    )

    test_class_metrics = (
        classification_metrics(
            test[
                CLASS_COLUMN
            ],
            test_class_pred,
        )
    )

    matrix = confusion_matrix(
        test[
            CLASS_COLUMN
        ],
        test_class_pred,
        labels=[0, 1, 2],
    )

    area_results = per_area_metrics(
        test,
        test_reg_pred,
        test_class_pred,
    )

    print()
    print("=" * 100)
    print("FINAL REGRESSION TEST")
    print("=" * 100)

    print(
        f"MAE:             "
        f"{test_reg_metrics['mae']:.4f}"
    )

    print(
        f"RMSE:            "
        f"{test_reg_metrics['rmse']:.4f}"
    )

    print(
        f"R²:              "
        f"{test_reg_metrics['r2']:.4f}"
    )

    print()
    print(
        f"Classification Accuracy: "
        f"{test_class_metrics['accuracy']:.4f}"
    )

    print(
        f"Classification Macro F1: "
        f"{test_class_metrics['macro_f1']:.4f}"
    )

    print(
        f"Classification Macro Precision: "
        f"{test_class_metrics['macro_precision']:.4f}"
    )

    print(
        f"Classification Macro Recall: "
        f"{test_class_metrics['macro_recall']:.4f}"
    )

    print()
    print("Confusion matrix:")

    print(
        matrix
    )

    print()
    print("PER-AREA TEST RESULTS")
    print("-" * 80)

    for (
        area,
        values,
    ) in area_results.items():

        print(
            f"{area:<15} "
            f"MAE={values['regression']['mae']:.3f} | "
            f"R2={values['regression']['r2']:.3f} | "
            f"Macro F1={values['classification']['macro_f1']:.4f}"
        )

    # ==================================================================================
    # SAVE
    # ==================================================================================

    joblib.dump(
        best_model,
        BEST_MODEL_FILE,
    )

    final_metadata = {
        "experiment":
            "OceanEye Multi-Area Regression V4",

        "candidate":
            best_candidate,

        "validation_macro_f1":
            best_validation_macro_f1,

        "test_regression_metrics":
            test_reg_metrics,

        "test_classification_metrics":
            test_class_metrics,

        "test_confusion_matrix":
            matrix.tolist(),

        "per_area_test":
            area_results,

        "thresholds":
            thresholds,

        "features":
            feature_columns,
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

    # ==================================================================================
    # FIGURE
    # ==================================================================================

    classifier_macro_f1 = 0.6260

    regression_macro_f1 = (
        test_class_metrics[
            "macro_f1"
        ]
    )

    comparison = pd.DataFrame(
        {
            "approach": [
                "Direct classifier V2",
                "Regression + thresholds V4",
            ],
            "macro_f1": [
                classifier_macro_f1,
                regression_macro_f1,
            ],
        }
    )

    fig, ax = plt.subplots(
        figsize=(8, 5)
    )

    ax.bar(
        comparison[
            "approach"
        ],
        comparison[
            "macro_f1"
        ],
    )

    ax.set_ylim(
        0,
        1,
    )

    ax.set_ylabel(
        "Test Macro F1"
    )

    ax.set_title(
        "Direct classification vs regression-derived traffic level"
    )

    for index, value in enumerate(
        comparison[
            "macro_f1"
        ]
    ):

        ax.text(
            index,
            value + 0.02,
            f"{value:.3f}",
            ha="center",
        )

    fig.tight_layout()

    fig.savefig(
        FIGURE_FILE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print()
    print("=" * 100)
    print("SAVED ARTIFACTS")
    print("=" * 100)

    print(
        RESULTS_FILE
    )

    print(
        DETAILS_FILE
    )

    print(
        BEST_MODEL_FILE
    )

    print(
        BEST_METADATA_FILE
    )

    print(
        FIGURE_FILE
    )


if __name__ == "__main__":
    main()