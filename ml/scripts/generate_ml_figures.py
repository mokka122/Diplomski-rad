from pathlib import Path
import json

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


BASE_DIR = Path(__file__).resolve().parent.parent

RESULTS_DIR = BASE_DIR / "results"
MODELS_DIR = BASE_DIR / "models"
FEATURES_DIR = BASE_DIR / "data" / "features"

FIGURES_DIR = RESULTS_DIR / "figures"

FIGURES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================================================
# 1. BASELINE MODEL RANKING
# ======================================================================================

def plot_model_ranking():

    file_path = (
        RESULTS_DIR
        / "multi_area_validation_results.csv"
    )

    df = pd.read_csv(file_path)

    df = df.sort_values(
        "macro_f1",
        ascending=True,
    )

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    ax.barh(
        df["model"],
        df["macro_f1"],
    )

    ax.set_xlabel(
        "Validation Macro F1"
    )

    ax.set_ylabel(
        "Model"
    )

    ax.set_title(
        "Multi-Area model comparison – Validation Macro F1"
    )

    ax.set_xlim(
        0,
        max(
            0.7,
            df["macro_f1"].max() + 0.05,
        ),
    )

    for index, value in enumerate(
        df["macro_f1"]
    ):

        ax.text(
            value + 0.005,
            index,
            f"{value:.3f}",
            va="center",
        )

    fig.tight_layout()

    fig.savefig(
        FIGURES_DIR
        / "01_model_validation_macro_f1.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# 2. ACCURACY
# ======================================================================================

def plot_model_accuracy():

    file_path = (
        RESULTS_DIR
        / "multi_area_validation_results.csv"
    )

    df = pd.read_csv(file_path)

    df = df.sort_values(
        "accuracy",
        ascending=True,
    )

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    ax.barh(
        df["model"],
        df["accuracy"],
    )

    ax.set_xlabel(
        "Validation Accuracy"
    )

    ax.set_ylabel(
        "Model"
    )

    ax.set_title(
        "Multi-Area model comparison – Validation Accuracy"
    )

    ax.set_xlim(
        0,
        max(
            0.7,
            df["accuracy"].max() + 0.05,
        ),
    )

    fig.tight_layout()

    fig.savefig(
        FIGURES_DIR
        / "02_model_validation_accuracy.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# 3. TUNING
# ======================================================================================

def plot_tuning():

    file_path = (
        RESULTS_DIR
        / "multi_area_tuning_results.csv"
    )

    df = pd.read_csv(file_path)

    top = (
        df
        .sort_values(
            "macro_f1",
            ascending=False,
        )
        .head(15)
        .sort_values(
            "macro_f1",
            ascending=True,
        )
    )

    labels = (
        top["candidate_id"]
        + " | "
        + top["model_family"]
    )

    fig, ax = plt.subplots(
        figsize=(11, 7)
    )

    ax.barh(
        labels,
        top["macro_f1"],
    )

    ax.set_xlabel(
        "Validation Macro F1"
    )

    ax.set_title(
        "Top hyperparameter tuning candidates"
    )

    for index, value in enumerate(
        top["macro_f1"]
    ):

        ax.text(
            value + 0.001,
            index,
            f"{value:.4f}",
            va="center",
            fontsize=8,
        )

    fig.tight_layout()

    fig.savefig(
        FIGURES_DIR
        / "03_tuning_top_candidates.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# 4. CONFUSION MATRIX
# ======================================================================================

def plot_confusion_matrix():

    metadata_file = (
        MODELS_DIR
        / "traffic_classifier_multi_area_tuned_metadata.json"
    )

    with open(
        metadata_file,
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(file)

    matrix = np.array(
        metadata[
            "test_confusion_matrix"
        ]
    )

    labels = [
        "LOW",
        "MEDIUM",
        "HIGH",
    ]

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

    ax.set(
        xticks=np.arange(
            len(labels)
        ),
        yticks=np.arange(
            len(labels)
        ),
        xticklabels=labels,
        yticklabels=labels,
        ylabel="Actual class",
        xlabel="Predicted class",
        title="XGBoost final test confusion matrix",
    )

    threshold = (
        matrix.max()
        / 2
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
        FIGURES_DIR
        / "04_final_confusion_matrix.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# 5. PER AREA F1
# ======================================================================================

def plot_per_area_f1():

    metadata_file = (
        MODELS_DIR
        / "traffic_classifier_multi_area_tuned_metadata.json"
    )

    with open(
        metadata_file,
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(file)

    values = []

    for (
        area,
        metrics,
    ) in metadata[
        "per_area_test"
    ].items():

        values.append(
            {
                "study_area":
                    area,

                "macro_f1":
                    metrics[
                        "macro_f1"
                    ],
            }
        )

    df = (
        pd.DataFrame(values)
        .sort_values(
            "macro_f1",
            ascending=True,
        )
    )

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    ax.barh(
        df["study_area"],
        df["macro_f1"],
    )

    ax.set_xlabel(
        "Test Macro F1"
    )

    ax.set_ylabel(
        "Study area"
    )

    ax.set_title(
        "XGBoost generalization by study area"
    )

    ax.set_xlim(
        0,
        1,
    )

    for index, value in enumerate(
        df["macro_f1"]
    ):

        ax.text(
            value + 0.01,
            index,
            f"{value:.3f}",
            va="center",
        )

    fig.tight_layout()

    fig.savefig(
        FIGURES_DIR
        / "05_per_area_macro_f1.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# 6. CLASS DISTRIBUTION
# ======================================================================================

def plot_class_distribution():

    df = pd.read_csv(
        FEATURES_DIR
        / "multi_area_ml_dataset.csv",
        usecols=[
            "dataset_split",
            "traffic_level",
        ],
    )

    counts = (
        df
        .groupby(
            [
                "dataset_split",
                "traffic_level",
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
    )

    counts = counts.reindex(
        [
            "train",
            "validation",
            "test",
        ]
    )

    counts = counts[
        [
            "LOW",
            "MEDIUM",
            "HIGH",
        ]
    ]

    fig, ax = plt.subplots(
        figsize=(9, 6)
    )

    counts.plot(
        kind="bar",
        ax=ax,
    )

    ax.set_xlabel(
        "Dataset split"
    )

    ax.set_ylabel(
        "Number of observations"
    )

    ax.set_title(
        "Traffic class distribution by temporal split"
    )

    ax.tick_params(
        axis="x",
        rotation=0,
    )

    fig.tight_layout()

    fig.savefig(
        FIGURES_DIR
        / "06_class_distribution_by_split.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# 7. DISTRIBUTION BY AREA
# ======================================================================================

def plot_class_distribution_area():

    df = pd.read_csv(
        FEATURES_DIR
        / "multi_area_ml_dataset.csv",
        usecols=[
            "study_area",
            "traffic_level",
        ],
    )

    counts = (
        df
        .groupby(
            [
                "study_area",
                "traffic_level",
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
    )

    counts = counts[
        [
            "LOW",
            "MEDIUM",
            "HIGH",
        ]
    ]

    fig, ax = plt.subplots(
        figsize=(11, 6)
    )

    counts.plot(
        kind="bar",
        ax=ax,
    )

    ax.set_xlabel(
        "Study area"
    )

    ax.set_ylabel(
        "Number of hourly observations"
    )

    ax.set_title(
        "Traffic class distribution by study area"
    )

    ax.tick_params(
        axis="x",
        rotation=30,
    )

    fig.tight_layout()

    fig.savefig(
        FIGURES_DIR
        / "07_class_distribution_by_area.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ======================================================================================
# MAIN
# ======================================================================================

def main():

    print(
        "Generating OceanEye ML figures..."
    )

    plot_model_ranking()
    print(
        "01_model_validation_macro_f1.png"
    )

    plot_model_accuracy()
    print(
        "02_model_validation_accuracy.png"
    )

    plot_tuning()
    print(
        "03_tuning_top_candidates.png"
    )

    plot_confusion_matrix()
    print(
        "04_final_confusion_matrix.png"
    )

    plot_per_area_f1()
    print(
        "05_per_area_macro_f1.png"
    )

    plot_class_distribution()
    print(
        "06_class_distribution_by_split.png"
    )

    plot_class_distribution_area()
    print(
        "07_class_distribution_by_area.png"
    )

    print()
    print(
        f"Figures saved to: "
        f"{FIGURES_DIR}"
    )


if __name__ == "__main__":
    main()