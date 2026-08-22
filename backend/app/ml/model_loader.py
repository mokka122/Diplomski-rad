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
    Loads and caches the final OceanEye production traffic model.
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

        if self._model is not None:
            return self._model

        if not MODEL_FILE.exists():
            return None

        self._model = joblib.load(
            MODEL_FILE
        )

        self._loaded_model_path = (
            MODEL_FILE
        )

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

            self._metadata = json.load(
                file
            )

        return self._metadata

    def get_metadata(self) -> Optional[dict]:
        return self.load_metadata()

    # ==================================================================================
    # MODEL NAME
    # ==================================================================================

    def get_model_name(self) -> Optional[str]:

        metadata = (
            self.get_metadata()
            or {}
        )

        model_family = (
            metadata.get(
                "model_family"
            )
        )

        candidate_id = (
            metadata.get(
                "candidate_id"
            )
        )

        if (
            model_family
            and candidate_id
        ):
            return (
                f"{model_family} "
                f"({candidate_id})"
            )

        if model_family:
            return model_family

        return (
            metadata.get(
                "selected_model"
            )
        )

    # ==================================================================================
    # RELOAD
    # ==================================================================================

    def reload(self) -> bool:

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

        return {
            "model_available":
                self.model_exists,

            "model_loaded":
                self.is_loaded,

            "metadata_available":
                self.metadata_exists,

            "model_path":
                str(
                    MODEL_FILE
                ),

            "metadata_path":
                str(
                    MODEL_METADATA_FILE
                ),

            "selected_model":
                self.get_model_name(),
        }


model_loader = ModelLoader()