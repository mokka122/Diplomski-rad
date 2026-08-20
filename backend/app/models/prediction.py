from typing import Dict, Optional

from pydantic import BaseModel, Field


class TrafficPredictionRequest(BaseModel):
    # ==================================================================================
    # CURRENT HOUR
    # ==================================================================================

    total_events: float = Field(
        ge=0,
        description="Total maritime events during the current hour",
    )

    arrivals: float = Field(
        ge=0,
        description="Arrivals during the current hour",
    )

    departures: float = Field(
        ge=0,
        description="Departures during the current hour",
    )

    unique_vessels: float = Field(
        ge=0,
        description="Unique vessels observed during the current hour",
    )

    # ==================================================================================
    # CURRENT VESSEL-GROUP COMPOSITION
    # ==================================================================================

    passenger_events: float = Field(
        ge=0
    )

    cargo_events: float = Field(
        ge=0
    )

    fishing_events: float = Field(
        ge=0
    )

    tanker_events: float = Field(
        ge=0
    )

    auxiliary_events: float = Field(
        ge=0
    )

    tug_events: float = Field(
        ge=0
    )

    # ==================================================================================
    # CALENDAR
    # ==================================================================================

    hour_local: int = Field(
        ge=0,
        le=23,
    )

    day_of_week: int = Field(
        ge=0,
        le=6,
    )

    month: int = Field(
        ge=1,
        le=12,
    )

    day_of_year: int = Field(
        ge=1,
        le=366,
    )

    is_weekend: int = Field(
        ge=0,
        le=1,
    )

    # ==================================================================================
    # TOTAL TRAFFIC LAGS
    # ==================================================================================

    total_events_lag_1h: float = Field(
        ge=0
    )

    total_events_lag_2h: float = Field(
        ge=0
    )

    total_events_lag_3h: float = Field(
        ge=0
    )

    total_events_lag_6h: float = Field(
        ge=0
    )

    total_events_lag_24h: float = Field(
        ge=0
    )

    # ==================================================================================
    # ARRIVAL LAGS
    # ==================================================================================

    arrivals_lag_1h: float = Field(
        ge=0
    )

    arrivals_lag_2h: float = Field(
        ge=0
    )

    arrivals_lag_3h: float = Field(
        ge=0
    )

    arrivals_lag_24h: float = Field(
        ge=0
    )

    # ==================================================================================
    # DEPARTURE LAGS
    # ==================================================================================

    departures_lag_1h: float = Field(
        ge=0
    )

    departures_lag_2h: float = Field(
        ge=0
    )

    departures_lag_3h: float = Field(
        ge=0
    )

    departures_lag_24h: float = Field(
        ge=0
    )

    # ==================================================================================
    # UNIQUE VESSEL LAGS
    # ==================================================================================

    unique_vessels_lag_1h: float = Field(
        ge=0
    )

    unique_vessels_lag_24h: float = Field(
        ge=0
    )

    # ==================================================================================
    # ROLLING FEATURES
    # ==================================================================================

    total_events_rolling_mean_3h: float = Field(
        ge=0
    )

    total_events_rolling_mean_6h: float = Field(
        ge=0
    )

    total_events_rolling_mean_24h: float = Field(
        ge=0
    )

    arrivals_rolling_mean_3h: float = Field(
        ge=0
    )

    arrivals_rolling_mean_6h: float = Field(
        ge=0
    )

    arrivals_rolling_mean_24h: float = Field(
        ge=0
    )

    # ==================================================================================
    # CYCLICAL TIME FEATURES
    # ==================================================================================

    hour_sin: float = Field(
        ge=-1,
        le=1,
    )

    hour_cos: float = Field(
        ge=-1,
        le=1,
    )

    day_of_week_sin: float = Field(
        ge=-1,
        le=1,
    )

    day_of_week_cos: float = Field(
        ge=-1,
        le=1,
    )

    month_sin: float = Field(
        ge=-1,
        le=1,
    )

    month_cos: float = Field(
        ge=-1,
        le=1,
    )


class TrafficPredictionResponse(BaseModel):
    traffic_level: str

    traffic_level_numeric: int

    confidence: Optional[float] = None

    probabilities: Optional[
        Dict[str, float]
    ] = None

    prediction_horizon_hours: int

    study_area: str

    model_name: Optional[str] = None


class ModelStatusResponse(BaseModel):
    model_available: bool

    model_loaded: bool

    metadata_available: bool

    model_path: str

    metadata_path: str

    selected_model: Optional[str] = None