from pathlib import Path
import json
import time
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

from tabpfn import TabPFNClassifier


warnings.filterwarnings("ignore")


# ======================================================================================
# PATHS
# ======================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FEATURES_DIR = BASE_DIR / "data" / "features"
RESULTS_DIR = BASE_DIR / "results"
MODELS_DIR = BASE_DIR / "models"
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
    / "tabpfn_v6_results.json"
)

PREDICTIONS_FILE = (
    RESULTS_DIR
    / "tabpfn_v6_test_predictions.csv"
)

COMPARISON_FIGURE = (
    FIGURES_DIR
    / "13_v2_xgboost_vs_v6_tabpfn.png"
)

PER_AREA_FIGURE = (
    FIGURES_DIR
    / "14_tabpfn_per_area_macro_f1.png"
)


# ======================================================================================
# CONFIG
# ======================================================================================

RANDOM_STATE = 42

TARGET_COLUMN = "traffic_level_numeric"

CLASS_NAMES = [
    "LOW",
    "MEDIUM",
    "HIGH",
]

GPU_AVAILABLE = torch.cuda.is_available()

DEVICE = (
    "cuda"
    if GPU_AVAILABLE
    else "cpu"
)


# ======================================================================================
# EXPERIMENT SIZE
# ======================================================================================
#
# TabPFN is fundamentally different from XGBoost.
#
# GPU:
#   use full training set first.
#
# CPU:
#   use a representative stratified subset because TabPFN inference
#   on 219k training samples is not practical on CPU.
#
# ======================================================================================

if GPU_AVAILABLE:

    TRAIN_SAMPLE_LIMIT = 10000

else:

    TRAIN_SAMPLE_LIMIT = 1000


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

def predict_in_batches(
    model,
    X,
    batch_size=256,
    label="Inference",
):

    predictions = []

    total_rows = len(X)

    print(
        f"{label}: {total_rows:,} rows "
        f"in batches of {batch_size}"
    )

    for start in range(
        0,
        total_rows,
        batch_size,
    ):

        end = min(
            start + batch_size,
            total_rows,
        )

        batch = X[
            start:end
        ]

        batch_predictions = (
            model.predict(
                batch
            )
        )

        predictions.append(
            batch_predictions
        )

        print(
            f"  {end:,}/{total_rows:,}",
            end="\r",
        )

    print()

    return np.concatenate(
        predictions
    )

# ======================================================================================
# STRATIFIED CPU SUBSET
# ======================================================================================

def build_stratified_subset(
    dataframe,
    sample_limit,
):

    if (
        sample_limit is None
        or len(dataframe) <= sample_limit
    ):

        return dataframe.copy()

    print()
    print("=" * 100)
    print("BUILDING STRATIFIED FOUNDATION-MODEL SUBSET")
    print("=" * 100)

    dataframe = dataframe.copy()

    dataframe[
        "stratum"
    ] = (
        dataframe[
            "study_area"
        ].astype(str)
        + "_"
        + dataframe[
            TARGET_COLUMN
        ].astype(str)
    )

    counts = (
        dataframe[
            "stratum"
        ]
        .value_counts()
    )

    selected = []

    allocated = 0

    strata = list(
        counts.index
    )

    for index, stratum in enumerate(
        strata
    ):

        stratum_df = dataframe.loc[
            dataframe[
                "stratum"
            ]
            == stratum
        ]

        if index == len(strata) - 1:

            requested = (
                sample_limit
                - allocated
            )

        else:

            proportion = (
                len(stratum_df)
                / len(dataframe)
            )

            requested = int(
                round(
                    proportion
                    * sample_limit
                )
            )

        requested = max(
            1,
            requested,
        )

        requested = min(
            requested,
            len(stratum_df),
        )

        sample = stratum_df.sample(
            n=requested,
            random_state=RANDOM_STATE,
        )

        selected.append(
            sample
        )

        allocated += len(
            sample
        )

    subset = pd.concat(
        selected,
        ignore_index=True,
    )

    # Correct possible rounding overflow.

    if len(subset) > sample_limit:

        subset = subset.sample(
            n=sample_limit,
            random_state=RANDOM_STATE,
        )

    subset = (
        subset
        .drop(
            columns=[
                "stratum"
            ]
        )
        .reset_index(
            drop=True
        )
    )

    print(
        f"Original train rows: "
        f"{len(dataframe):,}"
    )

    print(
        f"TabPFN train rows:   "
        f"{len(subset):,}"
    )

    print()
    print(
        "SUBSET CLASS DISTRIBUTION"
    )

    print(
        pd.crosstab(
            subset[
                "study_area"
            ],
            subset[
                TARGET_COLUMN
            ],
        ).to_string()
    )

    return subset


# ======================================================================================
# LOAD DATA
# ======================================================================================

def load_data():

    print("=" * 100)
    print("OCEANEYE V6 - TABPFN FOUNDATION MODEL")
    print("=" * 100)

    print(
        f"Device: {DEVICE}"
    )

    print(
        f"CUDA available: "
        f"{GPU_AVAILABLE}"
    )

    print(
        f"Train sample limit: "
        f"{TRAIN_SAMPLE_LIMIT}"
    )

    df = pd.read_csv(
        DATASET_FILE,
        low_memory=False,
    )

    with open(
        METADATA_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(
            file
        )

    numeric_features = metadata[
        "numeric_features"
    ]

    train = df.loc[
        df[
            "dataset_split"
        ]
        == "train"
    ].copy()

    validation = df.loc[
        df[
            "dataset_split"
        ]
        == "validation"
    ].copy()

    test = df.loc[
        df[
            "dataset_split"
        ]
        == "test"
    ].copy()

    train = build_stratified_subset(
        train,
        TRAIN_SAMPLE_LIMIT,
    )

    print()
    print(
        f"Final TabPFN train: "
        f"{len(train):,}"
    )

    print(
        f"Validation:         "
        f"{len(validation):,}"
    )

    print(
        f"Test:               "
        f"{len(test):,}"
    )

    return (
        df,
        metadata,
        numeric_features,
        train,
        validation,
        test,
    )


# ======================================================================================
# ENCODE STUDY AREA
# ======================================================================================

def prepare_features(
    train,
    validation,
    test,
    numeric_features,
):

    encoder = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False,
        dtype=np.float32,
    )

    train_area = encoder.fit_transform(
        train[
            [
                "study_area"
            ]
        ]
    )

    validation_area = encoder.transform(
        validation[
            [
                "study_area"
            ]
        ]
    )

    test_area = encoder.transform(
        test[
            [
                "study_area"
            ]
        ]
    )

    X_train_numeric = (
        train[
            numeric_features
        ]
        .to_numpy(
            dtype=np.float32
        )
    )

    X_validation_numeric = (
        validation[
            numeric_features
        ]
        .to_numpy(
            dtype=np.float32
        )
    )

    X_test_numeric = (
        test[
            numeric_features
        ]
        .to_numpy(
            dtype=np.float32
        )
    )

    X_train = np.concatenate(
        [
            X_train_numeric,
            train_area,
        ],
        axis=1,
    )

    X_validation = np.concatenate(
        [
            X_validation_numeric,
            validation_area,
        ],
        axis=1,
    )

    X_test = np.concatenate(
        [
            X_test_numeric,
            test_area,
        ],
        axis=1,
    )

    y_train = (
        train[
            TARGET_COLUMN
        ]
        .to_numpy(
            dtype=np.int64
        )
    )

    y_validation = (
        validation[
            TARGET_COLUMN
        ]
        .to_numpy(
            dtype=np.int64
        )
    )

    y_test = (
        test[
            TARGET_COLUMN
        ]
        .to_numpy(
            dtype=np.int64
        )
    )

    print()
    print(
        f"Encoded feature count: "
        f"{X_train.shape[1]}"
    )

    return (
        X_train,
        y_train,
        X_validation,
        y_validation,
        X_test,
        y_test,
        encoder,
    )


# ======================================================================================
# PER AREA
# ======================================================================================

def calculate_per_area(
    dataframe,
    predictions,
):

    temp = (
        dataframe
        .copy()
        .reset_index(
            drop=True
        )
    )

    temp[
        "prediction"
    ] = predictions

    results = {}

    for area in sorted(
        temp[
            "study_area"
        ].unique()
    ):

        area_df = temp.loc[
            temp[
                "study_area"
            ]
            == area
        ]

        results[
            area
        ] = calculate_metrics(
            area_df[
                TARGET_COLUMN
            ],
            area_df[
                "prediction"
            ],
        )

    return results


# ======================================================================================
# FIGURES
# ======================================================================================

def plot_comparison(
    tabpfn_macro_f1,
):

    dataframe = pd.DataFrame(
        {
            "model": [
                "XGBoost V2",
                "TabPFN V6",
            ],
            "macro_f1": [
                0.6260,
                tabpfn_macro_f1,
            ],
        }
    )

    fig, ax = plt.subplots(
        figsize=(7, 5)
    )

    ax.bar(
        dataframe[
            "model"
        ],
        dataframe[
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
        "XGBoost V2 vs TabPFN V6"
    )

    for index, value in enumerate(
        dataframe[
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
        COMPARISON_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )


def plot_per_area(
    per_area,
):

    dataframe = pd.DataFrame(
        [
            {
                "study_area": area,
                "macro_f1":
                    metrics[
                        "macro_f1"
                    ],
            }

            for area, metrics
            in per_area.items()
        ]
    )

    dataframe = (
        dataframe
        .sort_values(
            "macro_f1",
            ascending=True,
        )
    )

    fig, ax = plt.subplots(
        figsize=(8, 5)
    )

    ax.barh(
        dataframe[
            "study_area"
        ],
        dataframe[
            "macro_f1"
        ],
    )

    ax.set_xlim(
        0,
        1,
    )

    ax.set_xlabel(
        "Test Macro F1"
    )

    ax.set_title(
        "TabPFN V6 performance by study area"
    )

    fig.tight_layout()

    fig.savefig(
        PER_AREA_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
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
        metadata,
        numeric_features,
        train,
        validation,
        test,
    ) = load_data()

    (
        X_train,
        y_train,
        X_validation,
        y_validation,
        X_test,
        y_test,
        encoder,
    ) = prepare_features(
        train,
        validation,
        test,
        numeric_features,
    )

    print()
    print("=" * 100)
    print("INITIALIZING PRETRAINED TABPFN")
    print("=" * 100)

    model = TabPFNClassifier(
        device=DEVICE,
        ignore_pretraining_limits=False,
        memory_saving_mode=True,
        fit_mode="fit_preprocessors",
        inference_precision="autocast",
        random_state=RANDOM_STATE,
        show_progress_bar=False,
)

    print()
    print("=" * 100)
    print("FITTING TABPFN CONTEXT")
    print("=" * 100)

    start = time.perf_counter()

    model.fit(
        X_train,
        y_train,
    )

    fit_seconds = (
        time.perf_counter()
        - start
    )

    print(
        f"Fit/context time: "
        f"{fit_seconds:.2f} s"
    )

    # ==================================================================================
    # VALIDATION
    # ==================================================================================

    print()
    print("=" * 100)
    print("V6 VALIDATION")
    print("=" * 100)

    start = time.perf_counter()

    validation_predictions = (
        predict_in_batches(
            model,
            X_validation,
            batch_size=256,
            label="Validation inference",
        )
    )

    validation_seconds = (
        time.perf_counter()
        - start
    )

    validation_metrics = (
        calculate_metrics(
            y_validation,
            validation_predictions,
        )
    )

    print(
        f"Inference time: "
        f"{validation_seconds:.2f} s"
    )

    for key, value in (
        validation_metrics.items()
    ):

        print(
            f"{key:<18} "
            f"{value:.4f}"
        )

    # ==================================================================================
    # TEST
    # ==================================================================================

    print()
    print("=" * 100)
    print("V6 FINAL TEST")
    print("=" * 100)

    start = time.perf_counter()

    test_predictions = (
        predict_in_batches(
            model,
            X_test,
            batch_size=256,
            label="Test inference",
        )
    )

    test_seconds = (
        time.perf_counter()
        - start
    )

    test_metrics = calculate_metrics(
        y_test,
        test_predictions,
    )

    matrix = confusion_matrix(
        y_test,
        test_predictions,
        labels=[0, 1, 2],
    )

    report = classification_report(
        y_test,
        test_predictions,
        labels=[0, 1, 2],
        target_names=CLASS_NAMES,
        zero_division=0,
        output_dict=True,
    )

    per_area = calculate_per_area(
        test,
        test_predictions,
    )

    print(
        f"Inference time: "
        f"{test_seconds:.2f} s"
    )

    print()

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

    print()
    print(
        "Confusion matrix:"
    )

    print(
        matrix
    )

    print()
    print(
        "PER-AREA TEST MACRO F1"
    )

    print(
        "-" * 70
    )

    for area, metrics in (
        per_area.items()
    ):

        print(
            f"{area:<15} "
            f"{metrics['macro_f1']:.4f}"
        )

    # ==================================================================================
    # SAVE RESULTS
    # ==================================================================================

    result = {
        "experiment":
            "OceanEye V6 TabPFN Foundation Model",

        "model_family":
            "TabPFN",

        "device":
            DEVICE,

        "full_training_rows":
            int(
                (
                    df[
                        "dataset_split"
                    ]
                    == "train"
                ).sum()
            ),

        "tabpfn_training_rows":
            len(
                train
            ),

        "cpu_subset_used":
            not GPU_AVAILABLE,

        "fit_seconds":
            fit_seconds,

        "validation_inference_seconds":
            validation_seconds,

        "test_inference_seconds":
            test_seconds,

        "validation_metrics":
            validation_metrics,

        "test_metrics":
            test_metrics,

        "per_area_test":
            per_area,

        "confusion_matrix":
            matrix.tolist(),

        "classification_report":
            report,
    }

    with open(
        RESULTS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    prediction_output = (
        test[
            [
                "timestamp_utc",
                "study_area",
                "traffic_level",
                TARGET_COLUMN,
            ]
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    prediction_output[
        "tabpfn_prediction_numeric"
    ] = test_predictions

    mapping = {
        0: "LOW",
        1: "MEDIUM",
        2: "HIGH",
    }

    prediction_output[
        "tabpfn_prediction"
    ] = (
        prediction_output[
            "tabpfn_prediction_numeric"
        ]
        .map(
            mapping
        )
    )

    prediction_output.to_csv(
        PREDICTIONS_FILE,
        index=False,
        encoding="utf-8",
    )

    plot_comparison(
        test_metrics[
            "macro_f1"
        ]
    )

    plot_per_area(
        per_area
    )

    print()
    print("=" * 100)
    print("SAVED ARTIFACTS")
    print("=" * 100)

    print(
        RESULTS_FILE
    )

    print(
        PREDICTIONS_FILE
    )

    print(
        COMPARISON_FIGURE
    )

    print(
        PER_AREA_FIGURE
    )


if __name__ == "__main__":
    main()