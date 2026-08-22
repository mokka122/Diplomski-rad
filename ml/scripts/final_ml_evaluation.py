from pathlib import Path
import json
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
)


warnings.filterwarnings("ignore")


# ======================================================================================
# PATHS
# ======================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FEATURES_DIR = BASE_DIR / "data" / "features"
MODELS_DIR = BASE_DIR / "models"
LOCAL_MODELS_DIR = MODELS_DIR / "local"
RESULTS_DIR = BASE_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"


DATASET_FILE = (
    FEATURES_DIR
    / "multi_area_ml_dataset.csv"
)

ML_METADATA_FILE = (
    FEATURES_DIR
    / "multi_area_ml_metadata.json"
)

V2_MODEL_FILE = (
    MODELS_DIR
    / "traffic_classifier_multi_area_tuned.joblib"
)

V2_METADATA_FILE = (
    MODELS_DIR
    / "traffic_classifier_multi_area_tuned_metadata.json"
)

V4_METADATA_FILE = (
    MODELS_DIR
    / "traffic_regressor_multi_area_metadata.json"
)

V5_RESULTS_FILE = (
    RESULTS_DIR
    / "gru_v5_results.json"
)

V6_RESULTS_FILE = (
    RESULTS_DIR
    / "tabpfn_v6_results.json"
)

LOCAL_RESULTS_FILE = (
    RESULTS_DIR
    / "local_area_model_results.csv"
)

OUTPUT_CSV = (
    RESULTS_DIR
    / "ml_experiment_summary.csv"
)

OUTPUT_JSON = (
    RESULTS_DIR
    / "ml_experiment_summary.json"
)


# ======================================================================================
# FIGURES
# ======================================================================================

MACRO_F1_FIGURE = (
    FIGURES_DIR
    / "15_all_experiments_macro_f1.png"
)

ACCURACY_FIGURE = (
    FIGURES_DIR
    / "16_all_experiments_accuracy.png"
)

PER_AREA_FIGURE = (
    FIGURES_DIR
    / "17_per_area_model_comparison.png"
)

CONFUSION_MATRIX_FIGURE = (
    FIGURES_DIR
    / "18_final_xgboost_confusion_matrix.png"
)

FEATURE_IMPORTANCE_FIGURE = (
    FIGURES_DIR
    / "19_xgboost_feature_importance.png"
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

AREA_ORDER = [
    "Bergen",
    "Kristiansund",
    "Stavanger",
    "Tromsø",
    "Ålesund",
]


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
# LOAD BASE DATA
# ======================================================================================

def load_base_data():

    print("=" * 100)
    print("LOADING FINAL ML EVALUATION DATA")
    print("=" * 100)

    df = pd.read_csv(
        DATASET_FILE,
        low_memory=False,
    )

    with open(
        ML_METADATA_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        metadata = json.load(file)

    test = df.loc[
        df["dataset_split"] == "test"
    ].copy()

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

    print(
        f"Full dataset rows: {len(df):,}"
    )

    print(
        f"Test rows:         {len(test):,}"
    )

    print(
        f"Study areas:       {test['study_area'].nunique()}"
    )

    return (
        df,
        test,
        metadata,
        feature_columns,
    )


# ======================================================================================
# V2 GLOBAL XGBOOST
# ======================================================================================

def evaluate_v2(
    test,
    feature_columns,
):

    print()
    print("=" * 100)
    print("EVALUATING V2 - GLOBAL TUNED XGBOOST")
    print("=" * 100)

    model = joblib.load(
        V2_MODEL_FILE
    )

    X_test = test[
        feature_columns
    ]

    y_test = test[
        TARGET_COLUMN
    ].to_numpy()

    predictions = model.predict(
        X_test
    )

    metrics = calculate_metrics(
        y_test,
        predictions,
    )

    per_area = {}

    temp = test.copy()
    temp["prediction"] = predictions

    for area in AREA_ORDER:

        area_df = temp.loc[
            temp["study_area"] == area
        ]

        per_area[area] = calculate_metrics(
            area_df[TARGET_COLUMN],
            area_df["prediction"],
        )

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1, 2],
    )

    print(
        f"Macro F1: {metrics['macro_f1']:.4f}"
    )

    print(
        f"Accuracy: {metrics['accuracy']:.4f}"
    )

    return {
        "name":
            "V2 Global XGBoost",

        "short_name":
            "V2 XGBoost",

        "approach":
            "Direct multi-area classification",

        "metrics":
            metrics,

        "per_area":
            per_area,

        "confusion_matrix":
            matrix.tolist(),
    }


# ======================================================================================
# V3 LOCAL XGBOOST
# ======================================================================================

def safe_area_name(
    study_area,
):

    return (
        study_area
        .lower()
        .replace("å", "a")
        .replace("ø", "o")
        .replace("æ", "ae")
        .replace(" ", "_")
    )


def evaluate_v3(
    test,
    metadata,
):

    print()
    print("=" * 100)
    print("EVALUATING V3 - LOCAL XGBOOST MODELS")
    print("=" * 100)

    numeric_features = metadata[
        "numeric_features"
    ]

    local_features = [
        feature
        for feature in numeric_features
        if feature not in [
            "centroid_lat",
            "centroid_lon",
        ]
    ]

    combined_true = []
    combined_pred = []

    per_area = {}

    for area in AREA_ORDER:

        area_df = (
            test.loc[
                test["study_area"] == area
            ]
            .copy()
        )

        model_file = (
            LOCAL_MODELS_DIR
            / (
                "traffic_classifier_local_"
                f"{safe_area_name(area)}.joblib"
            )
        )

        if not model_file.exists():

            raise FileNotFoundError(
                f"Missing local model: {model_file}"
            )

        model = joblib.load(
            model_file
        )

        X_area = area_df[
            local_features
        ]

        y_area = (
            area_df[
                TARGET_COLUMN
            ]
            .to_numpy()
        )

        predictions = model.predict(
            X_area
        )

        area_metrics = calculate_metrics(
            y_area,
            predictions,
        )

        per_area[
            area
        ] = area_metrics

        combined_true.extend(
            y_area
        )

        combined_pred.extend(
            predictions
        )

    combined_true = np.asarray(
        combined_true
    )

    combined_pred = np.asarray(
        combined_pred
    )

    metrics = calculate_metrics(
        combined_true,
        combined_pred,
    )

    print(
        f"Pooled Macro F1: {metrics['macro_f1']:.4f}"
    )

    print(
        f"Pooled Accuracy: {metrics['accuracy']:.4f}"
    )

    return {
        "name":
            "V3 Local XGBoost",

        "short_name":
            "V3 Local",

        "approach":
            "Separate XGBoost model per study area",

        "metrics":
            metrics,

        "per_area":
            per_area,
    }


# ======================================================================================
# V4 REGRESSION + THRESHOLDS
# ======================================================================================

def load_v4():

    print()
    print("=" * 100)
    print("LOADING V4 - REGRESSION + THRESHOLDS")
    print("=" * 100)

    with open(
        V4_METADATA_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    metrics = data[
        "test_classification_metrics"
    ]

    per_area = {}

    for (
        area,
        values,
    ) in data[
        "per_area_test"
    ].items():

        per_area[
            area
        ] = values[
            "classification"
        ]

    print(
        f"Macro F1: {metrics['macro_f1']:.4f}"
    )

    print(
        f"Accuracy: {metrics['accuracy']:.4f}"
    )

    return {
        "name":
            "V4 XGBoost Regression",

        "short_name":
            "V4 Regression",

        "approach":
            "Count regression followed by area thresholds",

        "metrics":
            metrics,

        "per_area":
            per_area,

        "regression_metrics":
            data[
                "test_regression_metrics"
            ],
    }


# ======================================================================================
# V5 GRU
# ======================================================================================

def load_v5():

    print()
    print("=" * 100)
    print("LOADING V5 - GRU")
    print("=" * 100)

    with open(
        V5_RESULTS_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    metrics = data[
        "test_metrics"
    ]

    per_area = data[
        "per_area_test"
    ]

    print(
        f"Macro F1: {metrics['macro_f1']:.4f}"
    )

    print(
        f"Accuracy: {metrics['accuracy']:.4f}"
    )

    return {
        "name":
            "V5 GRU Sequence Model",

        "short_name":
            "V5 GRU",

        "approach":
            "48-hour deep temporal sequence classification",

        "metrics":
            metrics,

        "per_area":
            per_area,
    }


# ======================================================================================
# V6 TABPFN
# ======================================================================================

def load_v6():

    print()
    print("=" * 100)
    print("LOADING V6 - TABPFN")
    print("=" * 100)

    with open(
        V6_RESULTS_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    metrics = data[
        "test_metrics"
    ]

    per_area = data[
        "per_area_test"
    ]

    print(
        f"Macro F1: {metrics['macro_f1']:.4f}"
    )

    print(
        f"Accuracy: {metrics['accuracy']:.4f}"
    )

    return {
        "name":
            "V6 TabPFN Foundation Model",

        "short_name":
            "V6 TabPFN",

        "approach":
            "Pretrained tabular foundation model",

        "metrics":
            metrics,

        "per_area":
            per_area,

        "training_rows":
            data.get(
                "tabpfn_training_rows"
            ),

        "test_inference_seconds":
            data.get(
                "test_inference_seconds"
            ),
    }


# ======================================================================================
# SUMMARY TABLE
# ======================================================================================

def build_summary_table(
    experiments,
):

    rows = []

    for experiment in experiments:

        metrics = experiment[
            "metrics"
        ]

        rows.append(
            {
                "experiment":
                    experiment[
                        "short_name"
                    ],

                "approach":
                    experiment[
                        "approach"
                    ],

                "test_accuracy":
                    metrics[
                        "accuracy"
                    ],

                "test_macro_precision":
                    metrics[
                        "macro_precision"
                    ],

                "test_macro_recall":
                    metrics[
                        "macro_recall"
                    ],

                "test_macro_f1":
                    metrics[
                        "macro_f1"
                    ],

                "test_weighted_f1":
                    metrics[
                        "weighted_f1"
                    ],
            }
        )

    summary = pd.DataFrame(
        rows
    )

    summary = (
        summary
        .sort_values(
            "test_macro_f1",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )

    return summary


# ======================================================================================
# PLOT 15 - GLOBAL MACRO F1
# ======================================================================================

def plot_macro_f1(
    summary,
):

    plot_df = (
        summary
        .sort_values(
            "test_macro_f1",
            ascending=True,
        )
    )

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    ax.barh(
        plot_df[
            "experiment"
        ],
        plot_df[
            "test_macro_f1"
        ],
    )

    ax.set_xlim(
        0,
        1,
    )

    ax.set_xlabel(
        "Test Macro F1"
    )

    ax.set_ylabel(
        "Experiment"
    )

    ax.set_title(
        "Final comparison of OceanEye ML experiments"
    )

    for index, value in enumerate(
        plot_df[
            "test_macro_f1"
        ]
    ):

        ax.text(
            value + 0.01,
            index,
            f"{value:.3f}",
            va="center",
        )

    fig.tight_layout()

    fig.savefig(
        MACRO_F1_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# PLOT 16 - ACCURACY
# ======================================================================================

def plot_accuracy(
    summary,
):

    plot_df = (
        summary
        .sort_values(
            "test_accuracy",
            ascending=True,
        )
    )

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    ax.barh(
        plot_df[
            "experiment"
        ],
        plot_df[
            "test_accuracy"
        ],
    )

    ax.set_xlim(
        0,
        1,
    )

    ax.set_xlabel(
        "Test Accuracy"
    )

    ax.set_ylabel(
        "Experiment"
    )

    ax.set_title(
        "Test accuracy across OceanEye ML experiments"
    )

    for index, value in enumerate(
        plot_df[
            "test_accuracy"
        ]
    ):

        ax.text(
            value + 0.01,
            index,
            f"{value:.3f}",
            va="center",
        )

    fig.tight_layout()

    fig.savefig(
        ACCURACY_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# PLOT 17 - PER AREA
# ======================================================================================

def plot_per_area(
    experiments,
):

    rows = []

    for experiment in experiments:

        for area in AREA_ORDER:

            area_metrics = (
                experiment[
                    "per_area"
                ].get(
                    area
                )
            )

            if not area_metrics:
                continue

            rows.append(
                {
                    "study_area":
                        area,

                    "experiment":
                        experiment[
                            "short_name"
                        ],

                    "macro_f1":
                        area_metrics[
                            "macro_f1"
                        ],
                }
            )

    dataframe = pd.DataFrame(
        rows
    )

    pivot = (
        dataframe
        .pivot(
            index="study_area",
            columns="experiment",
            values="macro_f1",
        )
        .reindex(
            AREA_ORDER
        )
    )

    fig, ax = plt.subplots(
        figsize=(13, 7)
    )

    pivot.plot(
        kind="bar",
        ax=ax,
    )

    ax.set_ylim(
        0,
        1,
    )

    ax.set_xlabel(
        "Study area"
    )

    ax.set_ylabel(
        "Test Macro F1"
    )

    ax.set_title(
        "Per-area performance across ML approaches"
    )

    ax.tick_params(
        axis="x",
        rotation=25,
    )

    ax.legend(
        title="Experiment",
    )

    fig.tight_layout()

    fig.savefig(
        PER_AREA_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# PLOT 18 - FINAL CONFUSION MATRIX
# ======================================================================================

def plot_confusion_matrix(
    v2,
):

    matrix = np.asarray(
        v2[
            "confusion_matrix"
        ]
    )

    fig, ax = plt.subplots(
        figsize=(7, 6)
    )

    image = ax.imshow(
        matrix,
        interpolation="nearest",
    )

    fig.colorbar(
        image,
        ax=ax,
    )

    ax.set_xticks(
        np.arange(
            len(CLASS_NAMES)
        )
    )

    ax.set_yticks(
        np.arange(
            len(CLASS_NAMES)
        )
    )

    ax.set_xticklabels(
        CLASS_NAMES
    )

    ax.set_yticklabels(
        CLASS_NAMES
    )

    ax.set_xlabel(
        "Predicted traffic level"
    )

    ax.set_ylabel(
        "Actual traffic level"
    )

    ax.set_title(
        "Final tuned XGBoost test confusion matrix"
    )

    for i in range(
        matrix.shape[0]
    ):

        for j in range(
            matrix.shape[1]
        ):

            ax.text(
                j,
                i,
                f"{matrix[i, j]:,}",
                ha="center",
                va="center",
            )

    fig.tight_layout()

    fig.savefig(
        CONFUSION_MATRIX_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# PLOT 19 - XGBOOST FEATURE IMPORTANCE
# ======================================================================================

def plot_feature_importance():

    print()
    print("=" * 100)
    print("EXTRACTING XGBOOST FEATURE IMPORTANCE")
    print("=" * 100)

    pipeline = joblib.load(
        V2_MODEL_FILE
    )

    preprocessor = pipeline.named_steps[
        "preprocessor"
    ]

    estimator = pipeline.named_steps[
        "model"
    ]

    feature_names = (
        preprocessor
        .get_feature_names_out()
    )

    importance = estimator[
        "feature_importances_"
    ] if isinstance(
        estimator,
        dict,
    ) else estimator.feature_importances_

    if (
        len(feature_names)
        != len(importance)
    ):

        raise RuntimeError(
            "Feature name / importance length mismatch."
        )

    clean_names = []

    for name in feature_names:

        name = name.replace(
            "numeric__",
            "",
        )

        name = name.replace(
            "categorical__",
            "",
        )

        clean_names.append(
            name
        )

    dataframe = pd.DataFrame(
        {
            "feature":
                clean_names,

            "importance":
                importance,
        }
    )

    dataframe = (
        dataframe
        .sort_values(
            "importance",
            ascending=False,
        )
        .head(20)
        .sort_values(
            "importance",
            ascending=True,
        )
    )

    print()
    print(
        dataframe
        .sort_values(
            "importance",
            ascending=False,
        )
        .to_string(
            index=False
        )
    )

    fig, ax = plt.subplots(
        figsize=(10, 8)
    )

    ax.barh(
        dataframe[
            "feature"
        ],
        dataframe[
            "importance"
        ],
    )

    ax.set_xlabel(
        "XGBoost feature importance"
    )

    ax.set_ylabel(
        "Feature"
    )

    ax.set_title(
        "Top 20 features of the final tuned XGBoost model"
    )

    fig.tight_layout()

    fig.savefig(
        FEATURE_IMPORTANCE_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# SAVE JSON
# ======================================================================================

def save_json(
    summary,
    experiments,
):

    output = {
        "primary_metric":
            "test_macro_f1",

        "selected_production_model":
            "V2 Global XGBoost",

        "experiments":
            [],
    }

    for experiment in experiments:

        record = {
            "experiment":
                experiment[
                    "short_name"
                ],

            "name":
                experiment[
                    "name"
                ],

            "approach":
                experiment[
                    "approach"
                ],

            "metrics":
                experiment[
                    "metrics"
                ],

            "per_area":
                experiment[
                    "per_area"
                ],
        }

        if (
            "regression_metrics"
            in experiment
        ):

            record[
                "regression_metrics"
            ] = experiment[
                "regression_metrics"
            ]

        if (
            "training_rows"
            in experiment
        ):

            record[
                "training_rows"
            ] = experiment[
                "training_rows"
            ]

        if (
            "test_inference_seconds"
            in experiment
        ):

            record[
                "test_inference_seconds"
            ] = experiment[
                "test_inference_seconds"
            ]

        output[
            "experiments"
        ].append(
            record
        )

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )


# ======================================================================================
# MAIN
# ======================================================================================

def main():

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
        test,
        metadata,
        feature_columns,
    ) = load_base_data()

    v2 = evaluate_v2(
        test,
        feature_columns,
    )

    v3 = evaluate_v3(
        test,
        metadata,
    )

    v4 = load_v4()

    v5 = load_v5()

    v6 = load_v6()

    experiments = [
        v2,
        v3,
        v4,
        v5,
        v6,
    ]

    summary = build_summary_table(
        experiments
    )

    print()
    print("=" * 100)
    print("FINAL ML EXPERIMENT RANKING")
    print("=" * 100)

    print(
        summary[
            [
                "experiment",
                "test_macro_f1",
                "test_accuracy",
                "test_macro_precision",
                "test_macro_recall",
                "test_weighted_f1",
            ]
        ].to_string(
            index=False
        )
    )

    # ----------------------------------------------------------------------------------
    # Best model
    # ----------------------------------------------------------------------------------

    best = summary.iloc[0]

    print()
    print("=" * 100)
    print("SELECTED PRODUCTION MODEL")
    print("=" * 100)

    print(
        f"Experiment: "
        f"{best['experiment']}"
    )

    print(
        f"Test Macro F1: "
        f"{best['test_macro_f1']:.4f}"
    )

    print(
        f"Test Accuracy: "
        f"{best['test_accuracy']:.4f}"
    )

    # ----------------------------------------------------------------------------------
    # Save summary
    # ----------------------------------------------------------------------------------

    summary.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8",
    )

    save_json(
        summary,
        experiments,
    )

    # ----------------------------------------------------------------------------------
    # Figures
    # ----------------------------------------------------------------------------------

    plot_macro_f1(
        summary
    )

    plot_accuracy(
        summary
    )

    plot_per_area(
        experiments
    )

    plot_confusion_matrix(
        v2
    )

    plot_feature_importance()

    print()
    print("=" * 100)
    print("SAVED FINAL ML ARTIFACTS")
    print("=" * 100)

    print(
        OUTPUT_CSV
    )

    print(
        OUTPUT_JSON
    )

    print()
    print(
        MACRO_F1_FIGURE
    )

    print(
        ACCURACY_FIGURE
    )

    print(
        PER_AREA_FIGURE
    )

    print(
        CONFUSION_MATRIX_FIGURE
    )

    print(
        FEATURE_IMPORTANCE_FIGURE
    )


if __name__ == "__main__":
    main()