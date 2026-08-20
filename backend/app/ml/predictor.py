from typing import Any

import numpy as np
import pandas as pd

from app.ml.config import (
    FEATURE_COLUMNS,
    INVERSE_CLASS_MAPPING,
    PREDICTION_HORIZON_HOURS,
    STUDY_AREA,
)

from app.ml.model_loader import (
    model_loader,
)


class ModelNotAvailableError(Exception):
    """
    Raised when prediction is requested before
    a trained model is available.
    """


class TrafficPredictor:
    # ==================================================================================
    # INPUT PREPARATION
    # ==================================================================================

    def prepare_input(
        self,
        features: dict,
    ) -> pd.DataFrame:

        missing_features = [
            feature
            for feature in FEATURE_COLUMNS
            if feature not in features
        ]

        if missing_features:
            raise ValueError(
                "Missing ML features: "
                + ", ".join(
                    missing_features
                )
            )

        ordered_features = {
            feature: features[feature]
            for feature in FEATURE_COLUMNS
        }

        dataframe = pd.DataFrame(
            [
                ordered_features
            ],
            columns=FEATURE_COLUMNS,
        )

        return dataframe

    # ==================================================================================
    # PREDICTION
    # ==================================================================================

    def predict(
        self,
        features: dict,
    ) -> dict:

        model = model_loader.get_model()

        if model is None:
            raise ModelNotAvailableError(
                "Traffic prediction model is not available yet. "
                "Complete the ML training phase and place "
                "'traffic_classifier.joblib' in OceanEye/ml/models/."
            )

        input_dataframe = self.prepare_input(
            features
        )

        prediction = model.predict(
            input_dataframe
        )

        predicted_numeric = int(
            prediction[0]
        )

        traffic_level = (
            INVERSE_CLASS_MAPPING.get(
                predicted_numeric,
                str(predicted_numeric),
            )
        )

        confidence = None
        probabilities = None

        # ==================================================================================
        # CLASS PROBABILITIES
        # ==================================================================================

        if hasattr(
            model,
            "predict_proba",
        ):

            probability_array = (
                model.predict_proba(
                    input_dataframe
                )[0]
            )

            probabilities = {}

            model_classes = getattr(
                model,
                "classes_",
                range(
                    len(
                        probability_array
                    )
                ),
            )

            for class_value, probability in zip(
                model_classes,
                probability_array,
            ):

                numeric_class = int(
                    class_value
                )

                label = (
                    INVERSE_CLASS_MAPPING.get(
                        numeric_class,
                        str(
                            numeric_class
                        ),
                    )
                )

                probabilities[
                    label
                ] = float(
                    probability
                )

            confidence = float(
                np.max(
                    probability_array
                )
            )

        metadata = (
            model_loader.get_metadata()
            or {}
        )

        return {
            "traffic_level":
                traffic_level,

            "traffic_level_numeric":
                predicted_numeric,

            "confidence":
                confidence,

            "probabilities":
                probabilities,

            "prediction_horizon_hours":
                PREDICTION_HORIZON_HOURS,

            "study_area":
                STUDY_AREA,

            "model_name":
                metadata.get(
                    "selected_model"
                ),
        }


traffic_predictor = TrafficPredictor()