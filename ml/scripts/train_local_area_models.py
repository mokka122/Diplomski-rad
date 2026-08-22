from pathlib import Path
import json
import time
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
MODELS_DIR = BASE_DIR / "models" / "local"
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

GLOBAL_TUNING_DETAILS_FILE = (
    RESULTS_DIR
    / "multi_area_tuning_details.json"
)

GLOBAL_MODEL_METADATA_FILE = (
    BASE_DIR
    / "models"
    / "traffic_classifier_multi_area_tuned_metadata.json"
)

LOCAL_RESULTS_FILE = (
    RESULTS_DIR
    / "local_area_model_results.csv"
)

LOCAL_TUNING_RESULTS_FILE = (
    RESULTS_DIR
    / "local_area_tuning_results.csv"
)

LOCAL_DETAILS_FILE = (
    RESULTS_DIR
    / "local_area_model_details.json"
)

COMPARISON_FILE = (
    RESULTS_DIR
    / "global_vs_local_models.csv"
)

COMPARISON_FIGURE = (
    FIGURES_DIR
    / "08_global_vs_local_macro_f1.png"
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
# XGBOOST CANDIDATES
# ======================================================================================

CANDIDATES = [
    {
        "candidate_id": "LOCAL_XGB_01",
        "n_estimators": 300,
        "learning_rate": 0.03,
        "max_depth": 5,
        "min_child_weight": 1,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        "candidate_id": "LOCAL_XGB_02",
        "n_estimators": 400,
        "learning_rate": 0.03,
        "max_depth": 7,
        "min_child_weight": 1,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        "candidate_id": "LOCAL_XGB_03",
        "n_estimators": 500,
        "learning_rate": 0.03,
        "max_depth": 7,
        "min_child_weight": 3,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        "candidate_id": "LOCAL_XGB_04",
        "n_estimators": 350,
        "learning_rate": 0.05,
        "max_depth": 7,
        "min_child_weight": 3,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        # Global V2 winner configuration.
        "candidate_id": "LOCAL_XGB_05",
        "n_estimators": 400,
        "learning_rate": 0.04,
        "max_depth": 8,
        "min_child_weight": 5,
        "subsample": 0.9,
        "colsample_bytree": 0.85,
    },
    {
        "candidate_id": "LOCAL_XGB_06",
        "n_estimators": 350,
        "learning_rate": 0.05,
        "max_depth": 9,
        "min_child_weight": 3,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        "candidate_id": "LOCAL_XGB_07",
        "n_estimators": 300,
        "learning_rate": 0.07,
        "max_depth": 6,
        "min_child_weight": 3,
        "subsample": 0.85,
        "colsample_bytree": 0.9,
    },
]


# ======================================================================================
# METRICS
# ======================================================================================

def calculate_metrics(y_true, y_pred):

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

def load_dataset():

    print("=" * 100)
    print("LOADING MULTI-AREA DATASET FOR LOCAL MODELS")
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

    # Local models do not need geographic constants.
    # study_area is also omitted because every model contains only one area.

    local_features = [
        feature
        for feature in numeric_features
        if feature not in [
            "centroid_lat",
            "centroid_lon",
        ]
    ]

    print(
        f"Rows: {len(df):,}"
    )

    print(
        f"Local model features: "
        f"{len(local_features)}"
    )

    print(
        "Removed constant location features: "
        "centroid_lat, centroid_lon"
    )

    return (
        df,
        metadata,
        local_features,
    )


# ======================================================================================
# BUILD MODEL
# ======================================================================================

def build_model(candidate):

    params = {
        key: value
        for key, value in candidate.items()
        if key != "candidate_id"
    }

    return XGBClassifier(
        **params,
        objective="multi:softprob",
        eval_metric="mlogloss",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )


# ======================================================================================
# TRAIN ONE AREA
# ======================================================================================

def train_area(
    study_area,
    area_df,
    feature_columns,
):

    print()
    print("#" * 100)
    print(
        f"LOCAL MODEL: {study_area}"
    )
    print("#" * 100)

    train = area_df.loc[
        area_df["dataset_split"] == "train"
    ].copy()

    validation = area_df.loc[
        area_df["dataset_split"] == "validation"
    ].copy()

    test = area_df.loc[
        area_df["dataset_split"] == "test"
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
        f"Train:      {len(train):,}"
    )

    print(
        f"Validation: {len(validation):,}"
    )

    print(
        f"Test:       {len(test):,}"
    )

    print()
    print("TRAIN CLASS DISTRIBUTION")
    print(
        y_train
        .value_counts()
        .sort_index()
        .to_string()
    )

    tuning_rows = []

    best_model = None
    best_candidate = None
    best_validation_metrics = None
    best_validation_f1 = -1.0

    # ----------------------------------------------------------------------------------
    # Validation tuning
    # ----------------------------------------------------------------------------------

    for index, candidate in enumerate(
        CANDIDATES,
        start=1,
    ):

        candidate_id = candidate[
            "candidate_id"
        ]

        print()
        print(
            f"[{index}/{len(CANDIDATES)}] "
            f"{study_area} - {candidate_id}"
        )

        model = build_model(
            candidate
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

        validation_predictions = (
            model.predict(
                X_validation
            )
        )

        validation_metrics = (
            calculate_metrics(
                y_validation,
                validation_predictions,
            )
        )

        print(
            f"  time       = "
            f"{training_seconds:.2f} s"
        )

        print(
            f"  accuracy   = "
            f"{validation_metrics['accuracy']:.4f}"
        )

        print(
            f"  Macro F1   = "
            f"{validation_metrics['macro_f1']:.4f}"
        )

        tuning_rows.append(
            {
                "study_area":
                    study_area,

                "candidate_id":
                    candidate_id,

                "validation_macro_f1":
                    validation_metrics[
                        "macro_f1"
                    ],

                "validation_accuracy":
                    validation_metrics[
                        "accuracy"
                    ],

                "validation_macro_precision":
                    validation_metrics[
                        "macro_precision"
                    ],

                "validation_macro_recall":
                    validation_metrics[
                        "macro_recall"
                    ],

                "validation_weighted_f1":
                    validation_metrics[
                        "weighted_f1"
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

        if (
            validation_metrics[
                "macro_f1"
            ]
            > best_validation_f1
        ):

            best_validation_f1 = (
                validation_metrics[
                    "macro_f1"
                ]
            )

            best_model = model

            best_candidate = candidate

            best_validation_metrics = (
                validation_metrics
            )

    # ----------------------------------------------------------------------------------
    # Test exactly once after candidate selection
    # ----------------------------------------------------------------------------------

    print()
    print("=" * 100)
    print(
        f"BEST LOCAL VALIDATION MODEL - {study_area}"
    )
    print("=" * 100)

    print(
        best_candidate
    )

    print(
        f"Validation Macro F1: "
        f"{best_validation_f1:.4f}"
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
    print(
        f"TEST Accuracy:        "
        f"{test_metrics['accuracy']:.4f}"
    )

    print(
        f"TEST Macro Precision: "
        f"{test_metrics['macro_precision']:.4f}"
    )

    print(
        f"TEST Macro Recall:    "
        f"{test_metrics['macro_recall']:.4f}"
    )

    print(
        f"TEST Macro F1:        "
        f"{test_metrics['macro_f1']:.4f}"
    )

    print(
        f"TEST Weighted F1:     "
        f"{test_metrics['weighted_f1']:.4f}"
    )

    print()
    print("Confusion matrix:")

    print(
        test_matrix
    )

    # ----------------------------------------------------------------------------------
    # Save model
    # ----------------------------------------------------------------------------------

    safe_area_name = (
        study_area
        .lower()
        .replace("å", "a")
        .replace("ø", "o")
        .replace("æ", "ae")
        .replace(" ", "_")
    )

    model_file = (
        MODELS_DIR
        / f"traffic_classifier_local_{safe_area_name}.joblib"
    )

    metadata_file = (
        MODELS_DIR
        / f"traffic_classifier_local_{safe_area_name}_metadata.json"
    )

    joblib.dump(
        best_model,
        model_file,
    )

    area_metadata = {
        "experiment":
            "OceanEye Local Model V3",

        "study_area":
            study_area,

        "model_family":
            "XGBoost",

        "candidate_id":
            best_candidate[
                "candidate_id"
            ],

        "parameters": {
            key: value
            for key, value
            in best_candidate.items()
            if key != "candidate_id"
        },

        "selection_metric":
            "validation_macro_f1",

        "validation_metrics":
            best_validation_metrics,

        "test_metrics":
            test_metrics,

        "test_confusion_matrix":
            test_matrix.tolist(),

        "test_classification_report":
            test_report,

        "features":
            feature_columns,

        "model_file":
            str(model_file),
    }

    with open(
        metadata_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            area_metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    result = {
        "study_area":
            study_area,

        "candidate_id":
            best_candidate[
                "candidate_id"
            ],

        "validation_macro_f1":
            best_validation_metrics[
                "macro_f1"
            ],

        "validation_accuracy":
            best_validation_metrics[
                "accuracy"
            ],

        "test_macro_f1":
            test_metrics[
                "macro_f1"
            ],

        "test_accuracy":
            test_metrics[
                "accuracy"
            ],

        "test_macro_precision":
            test_metrics[
                "macro_precision"
            ],

        "test_macro_recall":
            test_metrics[
                "macro_recall"
            ],

        "test_weighted_f1":
            test_metrics[
                "weighted_f1"
            ],
    }

    details = {
        "best_candidate":
            area_metadata,

        "tuning":
            tuning_rows,
    }

    return (
        result,
        tuning_rows,
        details,
    )


# ======================================================================================
# LOAD GLOBAL V2 RESULTS
# ======================================================================================

def load_global_results():

    global_validation = {}
    global_test = {}

    # Validation per-area values for XGB_08.
    if GLOBAL_TUNING_DETAILS_FILE.exists():

        with open(
            GLOBAL_TUNING_DETAILS_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            tuning_details = json.load(
                file
            )

        if "XGB_08" in tuning_details:

            global_validation = (
                tuning_details[
                    "XGB_08"
                ]
                .get(
                    "per_area_validation",
                    {},
                )
            )

    # Test per-area values for final tuned model.
    if GLOBAL_MODEL_METADATA_FILE.exists():

        with open(
            GLOBAL_MODEL_METADATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            global_metadata = json.load(
                file
            )

        global_test = (
            global_metadata.get(
                "per_area_test",
                {},
            )
        )

    return (
        global_validation,
        global_test,
    )


# ======================================================================================
# GLOBAL VS LOCAL COMPARISON
# ======================================================================================

def build_comparison(
    local_results,
):

    (
        global_validation,
        global_test,
    ) = load_global_results()

    rows = []

    for local_row in local_results:

        area = local_row[
            "study_area"
        ]

        global_validation_f1 = (
            global_validation
            .get(
                area,
                {},
            )
            .get(
                "macro_f1",
                np.nan,
            )
        )

        global_test_f1 = (
            global_test
            .get(
                area,
                {},
            )
            .get(
                "macro_f1",
                np.nan,
            )
        )

        local_validation_f1 = (
            local_row[
                "validation_macro_f1"
            ]
        )

        local_test_f1 = (
            local_row[
                "test_macro_f1"
            ]
        )

        rows.append(
            {
                "study_area":
                    area,

                "global_validation_macro_f1":
                    global_validation_f1,

                "local_validation_macro_f1":
                    local_validation_f1,

                "validation_improvement":
                    (
                        local_validation_f1
                        -
                        global_validation_f1
                    ),

                "global_test_macro_f1":
                    global_test_f1,

                "local_test_macro_f1":
                    local_test_f1,

                "test_improvement":
                    (
                        local_test_f1
                        -
                        global_test_f1
                    ),
            }
        )

    comparison = pd.DataFrame(
        rows
    )

    comparison.to_csv(
        COMPARISON_FILE,
        index=False,
        encoding="utf-8",
    )

    return comparison


# ======================================================================================
# COMPARISON FIGURE
# ======================================================================================

def plot_comparison(
    comparison,
):

    plot_df = (
        comparison
        .sort_values(
            "local_test_macro_f1",
            ascending=True,
        )
        .copy()
    )

    y = np.arange(
        len(plot_df)
    )

    height = 0.35

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    ax.barh(
        y - height / 2,
        plot_df[
            "global_test_macro_f1"
        ],
        height,
        label="Global V2",
    )

    ax.barh(
        y + height / 2,
        plot_df[
            "local_test_macro_f1"
        ],
        height,
        label="Local V3",
    )

    ax.set_yticks(
        y
    )

    ax.set_yticklabels(
        plot_df[
            "study_area"
        ]
    )

    ax.set_xlim(
        0,
        1,
    )

    ax.set_xlabel(
        "Test Macro F1"
    )

    ax.set_ylabel(
        "Study area"
    )

    ax.set_title(
        "Global V2 vs Local V3 models"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        COMPARISON_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


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
        local_features,
    ) = load_dataset()

    study_areas = sorted(
        df[
            "study_area"
        ]
        .unique()
    )

    all_results = []
    all_tuning_rows = []
    all_details = {}

    print()
    print("=" * 100)
    print("OCEANEYE V3 - LOCAL AREA MODELS")
    print("=" * 100)

    print(
        f"Study areas: {len(study_areas)}"
    )

    print(
        f"Candidates per area: "
        f"{len(CANDIDATES)}"
    )

    print(
        f"Total model fits: "
        f"{len(study_areas) * len(CANDIDATES)}"
    )

    for study_area in study_areas:

        area_df = df.loc[
            df[
                "study_area"
            ]
            == study_area
        ].copy()

        (
            result,
            tuning_rows,
            details,
        ) = train_area(
            study_area=study_area,
            area_df=area_df,
            feature_columns=local_features,
        )

        all_results.append(
            result
        )

        all_tuning_rows.extend(
            tuning_rows
        )

        all_details[
            study_area
        ] = details

    # ----------------------------------------------------------------------------------
    # Save local results
    # ----------------------------------------------------------------------------------

    results_df = pd.DataFrame(
        all_results
    )

    results_df = (
        results_df
        .sort_values(
            "test_macro_f1",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )

    results_df.to_csv(
        LOCAL_RESULTS_FILE,
        index=False,
        encoding="utf-8",
    )

    tuning_df = pd.DataFrame(
        all_tuning_rows
    )

    tuning_df.to_csv(
        LOCAL_TUNING_RESULTS_FILE,
        index=False,
        encoding="utf-8",
    )

    with open(
        LOCAL_DETAILS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            all_details,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # ----------------------------------------------------------------------------------
    # Comparison
    # ----------------------------------------------------------------------------------

    comparison = build_comparison(
        all_results
    )

    plot_comparison(
        comparison
    )

    # ----------------------------------------------------------------------------------
    # Final report
    # ----------------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("LOCAL V3 RESULTS")
    print("=" * 100)

    print(
        results_df[
            [
                "study_area",
                "candidate_id",
                "validation_macro_f1",
                "test_macro_f1",
                "test_accuracy",
                "test_macro_precision",
                "test_macro_recall",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("=" * 100)
    print("GLOBAL V2 VS LOCAL V3")
    print("=" * 100)

    print(
        comparison[
            [
                "study_area",
                "global_test_macro_f1",
                "local_test_macro_f1",
                "test_improvement",
            ]
        ]
        .sort_values(
            "test_improvement",
            ascending=False,
        )
        .to_string(
            index=False
        )
    )

    valid_local = comparison[
        "local_test_macro_f1"
    ].dropna()

    valid_global = comparison[
        "global_test_macro_f1"
    ].dropna()

    print()
    print(
        f"Mean Global V2 area Macro F1: "
        f"{valid_global.mean():.4f}"
    )

    print(
        f"Mean Local V3 area Macro F1:  "
        f"{valid_local.mean():.4f}"
    )

    print(
        f"Mean improvement:              "
        f"{(valid_local.mean() - valid_global.mean()):+.4f}"
    )

    print()
    print("=" * 100)
    print("SAVED ARTIFACTS")
    print("=" * 100)

    print(
        LOCAL_RESULTS_FILE
    )

    print(
        LOCAL_TUNING_RESULTS_FILE
    )

    print(
        LOCAL_DETAILS_FILE
    )

    print(
        COMPARISON_FILE
    )

    print(
        COMPARISON_FIGURE
    )

    print()
    print(
        f"Local models directory:\n"
        f"{MODELS_DIR}"
    )


if __name__ == "__main__":
    main()