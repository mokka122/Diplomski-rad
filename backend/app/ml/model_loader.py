import json
from pathlib import Path
from typing import Any, Optional

import joblib

from app.ml.config import (
    MODEL_FILE,
    MODEL_METADATA_FILE,
)


class ModelLoader:
    """
    Loads and caches the trained OceanEye traffic model.

    The backend is allowed to run without a trained model.

    This is intentional because the rest of OceanEye can be
    developed and tested before the ML training phase is completed.
    """

    def __init__(self) -> None:
        self._model: Optional[Any] = None
        self._metadata: Optional[dict] = None

        self._loaded_model_path: Optional[Path] = None

    # ==================================================================================
    # STATUS
    # ==================================================================================

    @property
    def model_exists(self) -> bool:
        return MODEL_FILE.exists()

    @property
    def metadata_exists(self) -> bool:
        return MODEL_METADATA_FILE.exists()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    # ==================================================================================
    # MODEL
    # ==================================================================================

    def load_model(self) -> Optional[Any]:
        """
        Load the model only when it exists.

        Returns:
            Trained sklearn model/pipeline,
            or None when no model has been trained yet.
        """

        if self._model is not None:
            return self._model

        if not MODEL_FILE.exists():
            return None

        self._model = joblib.load(
            MODEL_FILE
        )

        self._loaded_model_path = MODEL_FILE

        return self._model

    def get_model(self) -> Optional[Any]:
        return self.load_model()

    # ==================================================================================
    # METADATA
    # ==================================================================================

    def load_metadata(self) -> Optional[dict]:
        if self._metadata is not None:
            return self._metadata

        if not MODEL_METADATA_FILE.exists():
            return None

        with open(
            MODEL_METADATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            self._metadata = json.load(file)

        return self._metadata

    def get_metadata(self) -> Optional[dict]:
        return self.load_metadata()

    # ==================================================================================
    # RELOAD
    # ==================================================================================

    def reload(self) -> bool:
        """
        Clear the cached model and metadata and load them again.

        Useful after a newly trained model is placed in ml/models/.
        """

        self._model = None
        self._metadata = None
        self._loaded_model_path = None

        model = self.load_model()

        if model is not None:
            self.load_metadata()

        return model is not None

    # ==================================================================================
    # STATUS RESPONSE
    # ==================================================================================

    def get_status(self) -> dict:
        metadata = self.get_metadata()

        return {
            "model_available": self.model_exists,
            "model_loaded": self.is_loaded,
            "metadata_available": self.metadata_exists,

            "model_path": str(
                MODEL_FILE
            ),

            "metadata_path": str(
                MODEL_METADATA_FILE
            ),

            "selected_model": (
                metadata.get(
                    "selected_model"
                )
                if metadata
                else None
            ),
        }


model_loader = ModelLoader()