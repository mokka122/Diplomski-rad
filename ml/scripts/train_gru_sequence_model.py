from pathlib import Path
import copy
import json
import random
import time
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import torch
import torch.nn as nn

from torch.utils.data import (
    Dataset,
    DataLoader,
)

from sklearn.preprocessing import StandardScaler

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)


warnings.filterwarnings("ignore")


# ======================================================================================
# PATHS
# ======================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FEATURES_DIR = BASE_DIR / "data" / "features"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

INPUT_FILE = (
    FEATURES_DIR
    / "multi_area_hourly_features_2020_2025.csv"
)

ML_METADATA_FILE = (
    FEATURES_DIR
    / "multi_area_ml_metadata.json"
)

MODEL_FILE = (
    MODELS_DIR
    / "traffic_classifier_gru_v5.pt"
)

SCALER_FILE = (
    MODELS_DIR
    / "traffic_classifier_gru_v5_scaler.joblib"
)

METADATA_FILE = (
    MODELS_DIR
    / "traffic_classifier_gru_v5_metadata.json"
)

RESULTS_FILE = (
    RESULTS_DIR
    / "gru_v5_results.json"
)

TRAINING_HISTORY_FILE = (
    RESULTS_DIR
    / "gru_v5_training_history.csv"
)

TRAINING_FIGURE = (
    FIGURES_DIR
    / "10_gru_training_history.png"
)

COMPARISON_FIGURE = (
    FIGURES_DIR
    / "11_v2_xgboost_vs_v5_gru.png"
)

PER_AREA_FIGURE = (
    FIGURES_DIR
    / "12_gru_per_area_macro_f1.png"
)


# ======================================================================================
# RANDOM SEED
# ======================================================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ======================================================================================
# CONFIG
# ======================================================================================

SEQUENCE_LENGTH = 48

BATCH_SIZE = 256

MAX_EPOCHS = 40

PATIENCE = 6

LEARNING_RATE = 0.001

WEIGHT_DECAY = 1e-4


TRAFFIC_FEATURES = [
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

    "hour_sin",
    "hour_cos",

    "day_of_week_sin",
    "day_of_week_cos",

    "month_sin",
    "month_cos",

    "is_weekend",
]


AREA_ORDER = [
    "Bergen",
    "Kristiansund",
    "Stavanger",
    "Tromsø",
    "Ålesund",
]


CLASS_NAMES = [
    "LOW",
    "MEDIUM",
    "HIGH",
]


# ======================================================================================
# DEVICE
# ======================================================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


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
    print("LOADING HOURLY DATA FOR V5 GRU")
    print("=" * 100)

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    df[
        "timestamp_utc"
    ] = pd.to_datetime(
        df[
            "timestamp_utc"
        ],
        errors="coerce",
        utc=True,
    )

    with open(
        ML_METADATA_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(
            file
        )

    thresholds = metadata[
        "thresholds"
    ]

    df = (
        df
        .sort_values(
            [
                "study_area",
                "timestamp_utc",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    print(
        f"Rows: {len(df):,}"
    )

    print(
        f"Areas: {df['study_area'].nunique()}"
    )

    print(
        f"Sequence length: {SEQUENCE_LENGTH} h"
    )

    return (
        df,
        thresholds,
    )


# ======================================================================================
# SPLIT
# ======================================================================================

def get_split(
    timestamp,
):

    train_end = pd.Timestamp(
        "2025-01-01 00:00:00",
        tz="UTC",
    )

    validation_end = pd.Timestamp(
        "2025-10-01 00:00:00",
        tz="UTC",
    )

    if timestamp < train_end:
        return "train"

    if timestamp < validation_end:
        return "validation"

    return "test"


# ======================================================================================
# CLASS LABEL
# ======================================================================================

def traffic_class(
    area,
    future_events,
    thresholds,
):

    high_threshold = int(
        thresholds[
            area
        ][
            "high_threshold"
        ]
    )

    future_events = int(
        future_events
    )

    if future_events == 0:
        return 0

    if (
        future_events
        >= high_threshold
    ):
        return 2

    return 1


# ======================================================================================
# SCALER
# ======================================================================================

def fit_scaler(
    df,
):

    print()
    print("=" * 100)
    print("FITTING TRAIN-ONLY SCALER")
    print("=" * 100)

    train_mask = (
        df[
            "timestamp_utc"
        ]
        < pd.Timestamp(
            "2025-01-01 00:00:00",
            tz="UTC",
        )
    )

    scaler = StandardScaler()

    scaler.fit(
        df.loc[
            train_mask,
            TRAFFIC_FEATURES,
        ]
    )

    return scaler


# ======================================================================================
# BUILD SEQUENCES
# ======================================================================================

def build_sequences(
    df,
    scaler,
    thresholds,
):

    print()
    print("=" * 100)
    print("BUILDING TEMPORAL SEQUENCES")
    print("=" * 100)

    sequences = {
        "train": [],
        "validation": [],
        "test": [],
    }

    labels = {
        "train": [],
        "validation": [],
        "test": [],
    }

    areas = {
        "train": [],
        "validation": [],
        "test": [],
    }

    timestamps = {
        "train": [],
        "validation": [],
        "test": [],
    }

    for area_index, area in enumerate(
        AREA_ORDER
    ):

        area_df = (
            df.loc[
                df[
                    "study_area"
                ]
                == area
            ]
            .copy()
            .reset_index(
                drop=True
            )
        )

        feature_values = scaler.transform(
            area_df[
                TRAFFIC_FEATURES
            ]
        ).astype(
            np.float32
        )

        target_values = (
            area_df[
                "future_total_events_1h"
            ]
            .to_numpy()
        )

        time_values = (
            area_df[
                "timestamp_utc"
            ]
            .to_numpy()
        )

        for index in range(
            SEQUENCE_LENGTH - 1,
            len(area_df),
        ):

            future_events = (
                target_values[
                    index
                ]
            )

            if pd.isna(
                future_events
            ):
                continue

            timestamp = (
                pd.Timestamp(
                    time_values[
                        index
                    ]
                )
            )

            split = get_split(
                timestamp
            )

            start_index = (
                index
                - SEQUENCE_LENGTH
                + 1
            )

            sequence = (
                feature_values[
                    start_index:
                    index + 1
                ]
            )

            label = traffic_class(
                area,
                future_events,
                thresholds,
            )

            sequences[
                split
            ].append(
                sequence
            )

            labels[
                split
            ].append(
                label
            )

            areas[
                split
            ].append(
                area_index
            )

            timestamps[
                split
            ].append(
                timestamp
            )

    for split in [
        "train",
        "validation",
        "test",
    ]:

        sequences[
            split
        ] = np.asarray(
            sequences[
                split
            ],
            dtype=np.float32,
        )

        labels[
            split
        ] = np.asarray(
            labels[
                split
            ],
            dtype=np.int64,
        )

        areas[
            split
        ] = np.asarray(
            areas[
                split
            ],
            dtype=np.int64,
        )

        print()
        print(
            f"{split.upper()}"
        )

        print(
            f"  sequences = "
            f"{len(labels[split]):,}"
        )

        unique, counts = np.unique(
            labels[
                split
            ],
            return_counts=True,
        )

        print(
            "  class distribution:"
        )

        for class_id, count in zip(
            unique,
            counts,
        ):

            print(
                f"    {CLASS_NAMES[class_id]}: "
                f"{count:,}"
            )

    return (
        sequences,
        labels,
        areas,
        timestamps,
    )


# ======================================================================================
# DATASET
# ======================================================================================

class TrafficSequenceDataset(
    Dataset
):

    def __init__(
        self,
        sequences,
        areas,
        labels,
    ):

        self.sequences = (
            torch.tensor(
                sequences,
                dtype=torch.float32,
            )
        )

        self.areas = (
            torch.tensor(
                areas,
                dtype=torch.long,
            )
        )

        self.labels = (
            torch.tensor(
                labels,
                dtype=torch.long,
            )
        )

    def __len__(self):

        return len(
            self.labels
        )

    def __getitem__(
        self,
        index,
    ):

        return (
            self.sequences[
                index
            ],
            self.areas[
                index
            ],
            self.labels[
                index
            ],
        )


# ======================================================================================
# MODEL
# ======================================================================================

class TrafficGRU(
    nn.Module
):

    def __init__(
        self,
        input_size,
        number_of_areas,
    ):

        super().__init__()

        self.area_embedding = (
            nn.Embedding(
                num_embeddings=
                    number_of_areas,

                embedding_dim=8,
            )
        )

        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=128,
            num_layers=2,
            batch_first=True,
            dropout=0.25,
        )

        self.classifier = nn.Sequential(
            nn.Linear(
                128 + 8,
                64,
            ),

            nn.ReLU(),

            nn.Dropout(
                0.30
            ),

            nn.Linear(
                64,
                32,
            ),

            nn.ReLU(),

            nn.Dropout(
                0.20
            ),

            nn.Linear(
                32,
                3,
            ),
        )

    def forward(
        self,
        sequence,
        area,
    ):

        gru_output, _ = self.gru(
            sequence
        )

        temporal_state = (
            gru_output[
                :,
                -1,
                :
            ]
        )

        area_vector = (
            self.area_embedding(
                area
            )
        )

        combined = torch.cat(
            [
                temporal_state,
                area_vector,
            ],
            dim=1,
        )

        return self.classifier(
            combined
        )


# ======================================================================================
# CLASS WEIGHTS
# ======================================================================================

def calculate_class_weights(
    labels,
):

    counts = np.bincount(
        labels,
        minlength=3,
    )

    total = counts.sum()

    weights = (
        total
        /
        (
            3
            * counts
        )
    )

    print()
    print(
        "Training class weights:"
    )

    for index, weight in enumerate(
        weights
    ):

        print(
            f"  {CLASS_NAMES[index]}: "
            f"{weight:.4f}"
        )

    return torch.tensor(
        weights,
        dtype=torch.float32,
        device=DEVICE,
    )


# ======================================================================================
# PREDICT
# ======================================================================================

def predict(
    model,
    loader,
):

    model.eval()

    predictions = []
    targets = []

    with torch.no_grad():

        for (
            sequence,
            area,
            labels,
        ) in loader:

            sequence = sequence.to(
                DEVICE
            )

            area = area.to(
                DEVICE
            )

            output = model(
                sequence,
                area,
            )

            predicted = (
                output
                .argmax(
                    dim=1
                )
                .cpu()
                .numpy()
            )

            predictions.extend(
                predicted
            )

            targets.extend(
                labels.numpy()
            )

    return (
        np.asarray(
            targets
        ),
        np.asarray(
            predictions
        ),
    )


# ======================================================================================
# TRAIN
# ======================================================================================

def train_model(
    model,
    train_loader,
    validation_loader,
    train_labels,
):

    class_weights = (
        calculate_class_weights(
            train_labels
        )
    )

    criterion = nn.CrossEntropyLoss(
        weight=class_weights
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )

    scheduler = (
        torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=0.5,
            patience=2,
        )
    )

    best_state = None

    best_macro_f1 = -1.0

    epochs_without_improvement = 0

    history = []

    print()
    print("=" * 100)
    print("TRAINING GRU")
    print("=" * 100)

    print(
        f"Device: {DEVICE}"
    )

    for epoch in range(
        1,
        MAX_EPOCHS + 1,
    ):

        epoch_start = (
            time.perf_counter()
        )

        model.train()

        running_loss = 0.0

        samples = 0

        for (
            sequence,
            area,
            labels,
        ) in train_loader:

            sequence = sequence.to(
                DEVICE
            )

            area = area.to(
                DEVICE
            )

            labels = labels.to(
                DEVICE
            )

            optimizer.zero_grad()

            outputs = model(
                sequence,
                area,
            )

            loss = criterion(
                outputs,
                labels,
            )

            loss.backward()

            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                max_norm=1.0,
            )

            optimizer.step()

            running_loss += (
                loss.item()
                * len(labels)
            )

            samples += len(
                labels
            )

        train_loss = (
            running_loss
            / samples
        )

        (
            validation_true,
            validation_pred,
        ) = predict(
            model,
            validation_loader,
        )

        validation_metrics = (
            calculate_metrics(
                validation_true,
                validation_pred,
            )
        )

        validation_f1 = (
            validation_metrics[
                "macro_f1"
            ]
        )

        scheduler.step(
            validation_f1
        )

        current_lr = (
            optimizer
            .param_groups[0][
                "lr"
            ]
        )

        epoch_seconds = (
            time.perf_counter()
            - epoch_start
        )

        history.append(
            {
                "epoch":
                    epoch,

                "train_loss":
                    train_loss,

                "validation_macro_f1":
                    validation_f1,

                "validation_accuracy":
                    validation_metrics[
                        "accuracy"
                    ],

                "learning_rate":
                    current_lr,

                "epoch_seconds":
                    epoch_seconds,
            }
        )

        print(
            f"Epoch {epoch:02d} | "
            f"loss={train_loss:.4f} | "
            f"val F1={validation_f1:.4f} | "
            f"val acc={validation_metrics['accuracy']:.4f} | "
            f"lr={current_lr:.6f} | "
            f"{epoch_seconds:.1f}s"
        )

        if (
            validation_f1
            > best_macro_f1
            + 0.0001
        ):

            best_macro_f1 = (
                validation_f1
            )

            best_state = copy.deepcopy(
                model.state_dict()
            )

            epochs_without_improvement = 0

        else:

            epochs_without_improvement += 1

        if (
            epochs_without_improvement
            >= PATIENCE
        ):

            print()
            print(
                "Early stopping."
            )

            break

    model.load_state_dict(
        best_state
    )

    return (
        model,
        history,
        best_macro_f1,
    )


# ======================================================================================
# PER AREA
# ======================================================================================

def calculate_per_area(
    y_true,
    y_pred,
    area_indices,
):

    result = {}

    for area_index, area in enumerate(
        AREA_ORDER
    ):

        mask = (
            area_indices
            == area_index
        )

        result[
            area
        ] = calculate_metrics(
            y_true[
                mask
            ],
            y_pred[
                mask
            ],
        )

    return result


# ======================================================================================
# FIGURES
# ======================================================================================

def plot_training_history(
    history_df,
):

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    ax.plot(
        history_df[
            "epoch"
        ],
        history_df[
            "validation_macro_f1"
        ],
        marker="o",
    )

    ax.set_xlabel(
        "Epoch"
    )

    ax.set_ylabel(
        "Validation Macro F1"
    )

    ax.set_title(
        "GRU V5 validation performance"
    )

    fig.tight_layout()

    fig.savefig(
        TRAINING_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


def plot_comparison(
    gru_macro_f1,
):

    comparison = pd.DataFrame(
        {
            "model": [
                "XGBoost V2",
                "GRU V5",
            ],
            "macro_f1": [
                0.6260,
                gru_macro_f1,
            ],
        }
    )

    fig, ax = plt.subplots(
        figsize=(7, 5)
    )

    ax.bar(
        comparison[
            "model"
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
        "XGBoost V2 vs GRU V5"
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
        COMPARISON_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


def plot_per_area(
    per_area,
):

    dataframe = pd.DataFrame(
        [
            {
                "study_area":
                    area,

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
        "GRU V5 performance by study area"
    )

    fig.tight_layout()

    fig.savefig(
        PER_AREA_FIGURE,
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

    print("=" * 100)
    print("OCEANEYE V5 - DEEP TEMPORAL GRU")
    print("=" * 100)

    print(
        f"PyTorch device: {DEVICE}"
    )

    (
        df,
        thresholds,
    ) = load_data()

    scaler = fit_scaler(
        df
    )

    (
        sequences,
        labels,
        area_indices,
        timestamps,
    ) = build_sequences(
        df,
        scaler,
        thresholds,
    )

    train_dataset = (
        TrafficSequenceDataset(
            sequences[
                "train"
            ],
            area_indices[
                "train"
            ],
            labels[
                "train"
            ],
        )
    )

    validation_dataset = (
        TrafficSequenceDataset(
            sequences[
                "validation"
            ],
            area_indices[
                "validation"
            ],
            labels[
                "validation"
            ],
        )
    )

    test_dataset = (
        TrafficSequenceDataset(
            sequences[
                "test"
            ],
            area_indices[
                "test"
            ],
            labels[
                "test"
            ],
        )
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
    )

    validation_loader = DataLoader(
        validation_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    model = TrafficGRU(
        input_size=len(
            TRAFFIC_FEATURES
        ),
        number_of_areas=len(
            AREA_ORDER
        ),
    ).to(
        DEVICE
    )

    total_parameters = sum(
        parameter.numel()
        for parameter
        in model.parameters()
    )

    trainable_parameters = sum(
        parameter.numel()
        for parameter
        in model.parameters()
        if parameter.requires_grad
    )

    print()
    print(
        f"Total parameters: "
        f"{total_parameters:,}"
    )

    print(
        f"Trainable parameters: "
        f"{trainable_parameters:,}"
    )

    (
        model,
        history,
        best_validation_f1,
    ) = train_model(
        model,
        train_loader,
        validation_loader,
        labels[
            "train"
        ],
    )

    # ==================================================================================
    # TEST
    # ==================================================================================

    (
        y_test,
        y_test_pred,
    ) = predict(
        model,
        test_loader,
    )

    test_metrics = calculate_metrics(
        y_test,
        y_test_pred,
    )

    matrix = confusion_matrix(
        y_test,
        y_test_pred,
        labels=[0, 1, 2],
    )

    report = classification_report(
        y_test,
        y_test_pred,
        labels=[0, 1, 2],
        target_names=CLASS_NAMES,
        zero_division=0,
        output_dict=True,
    )

    per_area = calculate_per_area(
        y_test,
        y_test_pred,
        area_indices[
            "test"
        ],
    )

    print()
    print("=" * 100)
    print("V5 FINAL TEST")
    print("=" * 100)

    print(
        f"Best Validation Macro F1: "
        f"{best_validation_f1:.4f}"
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

    for (
        area,
        metrics,
    ) in per_area.items():

        print(
            f"{area:<15} "
            f"{metrics['macro_f1']:.4f}"
        )

    # ==================================================================================
    # SAVE MODEL
    # ==================================================================================

    torch.save(
        {
            "model_state_dict":
                model.state_dict(),

            "input_size":
                len(
                    TRAFFIC_FEATURES
                ),

            "sequence_length":
                SEQUENCE_LENGTH,

            "area_order":
                AREA_ORDER,

            "features":
                TRAFFIC_FEATURES,
        },
        MODEL_FILE,
    )

    joblib.dump(
        scaler,
        SCALER_FILE,
    )

    history_df = pd.DataFrame(
        history
    )

    history_df.to_csv(
        TRAINING_HISTORY_FILE,
        index=False,
        encoding="utf-8",
    )

    results = {
        "experiment":
            "OceanEye V5 Deep Temporal GRU",

        "device":
            str(
                DEVICE
            ),

        "sequence_length":
            SEQUENCE_LENGTH,

        "features":
            TRAFFIC_FEATURES,

        "areas":
            AREA_ORDER,

        "total_parameters":
            total_parameters,

        "trainable_parameters":
            trainable_parameters,

        "best_validation_macro_f1":
            best_validation_f1,

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
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )

    plot_training_history(
        history_df
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
        MODEL_FILE
    )

    print(
        SCALER_FILE
    )

    print(
        RESULTS_FILE
    )

    print(
        TRAINING_HISTORY_FILE
    )

    print(
        TRAINING_FIGURE
    )

    print(
        COMPARISON_FIGURE
    )

    print(
        PER_AREA_FIGURE
    )


if __name__ == "__main__":
    main()