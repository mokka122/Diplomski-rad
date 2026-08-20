from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.ml.model_loader import (
    model_loader,
)

from app.ml.predictor import (
    ModelNotAvailableError,
    traffic_predictor,
)

from app.models.prediction import (
    ModelStatusResponse,
    TrafficPredictionRequest,
    TrafficPredictionResponse,
)

from app.services.live_feature_builder import (
    live_feature_builder,
)


router = APIRouter(
    prefix="/prediction",
    tags=["Prediction"],
)


# ======================================================================================
# MODEL STATUS
# ======================================================================================

@router.get(
    "/status",
    response_model=ModelStatusResponse,
)
async def get_prediction_status():
    """
    Check whether the trained OceanEye ML model
    is currently available to the backend.
    """

    return model_loader.get_status()


# ======================================================================================
# MANUAL TRAFFIC PREDICTION
# ======================================================================================

@router.post(
    "/traffic",
    response_model=TrafficPredictionResponse,
)
async def predict_traffic(
    request: TrafficPredictionRequest,
):
    """
    Predict maritime traffic level in Ålesund
    for the following hour using manually supplied
    ML feature values.

    Expected classes:

    - LOW
    - MEDIUM
    - HIGH

    Until the training phase is completed,
    this endpoint intentionally returns HTTP 503.
    """

    try:
        features = request.model_dump()

        result = traffic_predictor.predict(
            features
        )

        return result

    except ModelNotAvailableError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Traffic prediction failed: "
                f"{exc}"
            ),
        ) from exc


# ======================================================================================
# LIVE TRAFFIC PREDICTION
# ======================================================================================

@router.get(
    "/live",
    response_model=TrafficPredictionResponse,
)
async def predict_live_traffic():
    """
    Build the current OceanEye live ML feature set
    directly from Redis hourly traffic data and use
    the trained model to predict traffic level for
    the following hour.

    Pipeline:

        BarentsWatch
            ->
        Kafka
            ->
        Ålesund geofence
            ->
        ENTRY / EXIT traffic events
            ->
        Redis hourly aggregates
            ->
        42 ML features
            ->
        TrafficPredictor

    Until a trained model exists, this endpoint
    intentionally returns HTTP 503.
    """

    try:
        live_data = (
            await live_feature_builder
            .build_features()
        )

        features = live_data[
            "features"
        ]

        result = traffic_predictor.predict(
            features
        )

        return result

    except ModelNotAvailableError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Live ML feature generation failed: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Live traffic prediction failed: "
                f"{exc}"
            ),
        ) from exc


# ======================================================================================
# LIVE FEATURE + MODEL DEBUG STATUS
# ======================================================================================

@router.get(
    "/live/status",
)
async def get_live_prediction_status():
    """
    Return live prediction readiness.

    Checks:

    - 42 feature contract
    - availability of required live history
    - trained model availability
    """

    live_data = (
        await live_feature_builder
        .build_features()
    )

    history_readiness = (
        await live_feature_builder
        .get_history_readiness()
    )

    model_status = (
        model_loader
        .get_status()
    )

    feature_contract_ready = (
        live_data[
            "feature_count"
        ]
        == 42
    )

    ready_for_prediction = (
        feature_contract_ready
        and history_readiness[
            "ready"
        ]
        and model_status[
            "model_available"
        ]
    )

    return {
        "ready_for_prediction":
            ready_for_prediction,

        "live_features_ready":
            feature_contract_ready,

        "live_history_ready":
            history_readiness[
                "ready"
            ],

        "feature_count":
            live_data[
                "feature_count"
            ],

        "reference_hour_utc":
            live_data[
                "reference_hour_utc"
            ],

        "prediction_target_hour_utc":
            live_data[
                "prediction_target_hour_utc"
            ],

        "history":
            history_readiness,

        "model_available":
            model_status[
                "model_available"
            ],

        "model_loaded":
            model_status[
                "model_loaded"
            ],

        "metadata_available":
            model_status[
                "metadata_available"
            ],

        "selected_model":
            model_status[
                "selected_model"
            ],
    }


# ======================================================================================
# MODEL RELOAD
# ======================================================================================

@router.post(
    "/reload",
)
async def reload_prediction_model():
    """
    Reload the trained model from disk.

    This endpoint is useful after the final ML training
    phase because the backend does not have to be restarted
    after traffic_classifier.joblib is created.
    """

    loaded = (
        model_loader
        .reload()
    )

    return {
        "reloaded": loaded,

        "status":
            model_loader
            .get_status(),
    }