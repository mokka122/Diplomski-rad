import math

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from zoneinfo import ZoneInfo

from app.ml.config import (
    FEATURE_COLUMNS,
    REQUIRED_HISTORY_HOURS,
    STUDY_AREA,
    STUDY_AREA_CENTROID_LAT,
    STUDY_AREA_CENTROID_LON,
)

from app.repositories.redis_traffic_repository import (
    RedisTrafficRepository,
)


OSLO_TIMEZONE = ZoneInfo(
    "Europe/Oslo"
)


class LiveFeatureBuilder:
    """
    Builds the live feature structure required by the
    final OceanEye Multi-Area V2 XGBoost model.

    Historical source:
        SafeSeaNet voyages

    Live source:
        BarentsWatch AIS
        -> geofence ENTRY / EXIT
        -> Redis hourly aggregates

    Final model contract:
        44 numeric features
        + 1 categorical feature: study_area
        = 45 model inputs

    Important methodological decisions:
        - only the latest fully completed hour is used
        - 25 consecutive hourly aggregates are required
        - rolling statistics exclude the reference hour
          because historical training used shift(1)
        - Ålesund is supplied as the live study-area context
    """

    def __init__(self):
        self.redis_repository = (
            RedisTrafficRepository()
        )

    # ==================================================================================
    # TIME
    # ==================================================================================

    def normalize_reference_hour(
        self,
        timestamp: datetime | None = None,
    ) -> datetime:
        """
        Return the latest fully completed UTC hour.

        Example:

            Current UTC time:
                2026-08-22 15:40

            Current incomplete hour:
                15:00-15:59

            Returned reference hour:
                14:00

        Historical ML features were created from complete hourly
        intervals, therefore live inference must follow the same
        temporal semantics.
        """

        if timestamp is None:
            timestamp = datetime.now(
                timezone.utc
            )

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )

        timestamp = timestamp.astimezone(
            timezone.utc
        )

        current_hour_start = (
            timestamp.replace(
                minute=0,
                second=0,
                microsecond=0,
            )
        )

        last_completed_hour = (
            current_hour_start
            - timedelta(
                hours=1
            )
        )

        return last_completed_hour

    # ==================================================================================
    # LOAD HISTORY
    # ==================================================================================

    async def _load_hourly_history(
        self,
        reference_hour: datetime,
    ) -> dict[int, dict]:
        """
        Load the reference hour and previous 24 hours.

        Dictionary keys represent lag:

            0  = reference hour
            1  = one hour before reference hour
            2  = two hours before
            ...
            24 = 24 hours before reference hour

        Total:
            25 consecutive hourly aggregates
        """

        history = {}

        for lag in range(
            REQUIRED_HISTORY_HOURS
        ):

            timestamp = (
                reference_hour
                - timedelta(
                    hours=lag
                )
            )

            history[
                lag
            ] = (
                await self.redis_repository
                .get_hour(
                    timestamp
                )
            )

        return history

    # ==================================================================================
    # ROLLING FEATURES
    # ==================================================================================

    def _rolling_mean(
        self,
        history: dict[int, dict],
        field: str,
        window: int,
    ) -> float:
        """
        Historical training used:

            series.shift(1).rolling(window)

        Therefore lag 0 MUST NOT be included in rolling features.

        Example for a 3-hour rolling mean:

            lag 1
            lag 2
            lag 3
        """

        values = []

        for lag in range(
            1,
            window + 1,
        ):

            hour = history.get(
                lag,
                {}
            )

            value = hour.get(
                field,
                0,
            )

            values.append(
                float(
                    value
                )
            )

        if not values:
            return 0.0

        return float(
            sum(
                values
            )
            / len(
                values
            )
        )

    # ==================================================================================
    # CALENDAR FEATURES
    # ==================================================================================

    def _calendar_features(
        self,
        reference_hour: datetime,
    ) -> dict:
        """
        Generate calendar and cyclical features in Europe/Oslo
        local time, matching historical feature engineering.
        """

        local_time = (
            reference_hour
            .astimezone(
                OSLO_TIMEZONE
            )
        )

        hour_local = (
            local_time.hour
        )

        day_of_week = (
            local_time.weekday()
        )

        month = (
            local_time.month
        )

        day_of_year = int(
            local_time.strftime(
                "%j"
            )
        )

        is_weekend = int(
            day_of_week
            in (
                5,
                6,
            )
        )

        return {
            "hour_local":
                hour_local,

            "day_of_week":
                day_of_week,

            "month":
                month,

            "day_of_year":
                day_of_year,

            "is_weekend":
                is_weekend,

            "hour_sin":
                math.sin(
                    2
                    * math.pi
                    * hour_local
                    / 24
                ),

            "hour_cos":
                math.cos(
                    2
                    * math.pi
                    * hour_local
                    / 24
                ),

            "day_of_week_sin":
                math.sin(
                    2
                    * math.pi
                    * day_of_week
                    / 7
                ),

            "day_of_week_cos":
                math.cos(
                    2
                    * math.pi
                    * day_of_week
                    / 7
                ),

            "month_sin":
                math.sin(
                    2
                    * math.pi
                    * (month - 1)
                    / 12
                ),

            "month_cos":
                math.cos(
                    2
                    * math.pi
                    * (month - 1)
                    / 12
                ),
        }

    # ==================================================================================
    # HISTORY READINESS
    # ==================================================================================

    async def get_history_readiness(
        self,
        timestamp: datetime | None = None,
    ) -> dict:
        """
        Verify that all 25 consecutive hourly Redis aggregates exist.

        This is stricter than checking only specific lag hours because
        rolling features require continuous historical coverage.
        """

        reference_hour = (
            self.normalize_reference_hour(
                timestamp
            )
        )

        availability = {}

        for lag in range(
            REQUIRED_HISTORY_HOURS
        ):

            hour = (
                reference_hour
                - timedelta(
                    hours=lag
                )
            )

            exists = (
                await self.redis_repository
                .hour_exists(
                    hour
                )
            )

            availability[
                f"lag_{lag}h"
            ] = {
                "timestamp_utc":
                    hour.isoformat(),

                "available":
                    bool(
                        exists
                    ),
            }

        available_count = sum(
            1
            for value
            in availability.values()
            if value[
                "available"
            ]
        )

        missing_hours = []

        for lag in range(
            REQUIRED_HISTORY_HOURS
        ):

            key = (
                f"lag_{lag}h"
            )

            if not availability[
                key
            ][
                "available"
            ]:

                missing_hours.append(
                    {
                        "lag_hours":
                            lag,

                        "timestamp_utc":
                            availability[
                                key
                            ][
                                "timestamp_utc"
                            ],
                    }
                )

        ready = (
            available_count
            == REQUIRED_HISTORY_HOURS
        )

        return {
            "ready":
                ready,

            "reference_hour_utc":
                reference_hour.isoformat(),

            "available_required_hours":
                available_count,

            "required_hours":
                REQUIRED_HISTORY_HOURS,

            "consecutive_history_required":
                True,

            "missing_hours":
                missing_hours,

            "availability":
                availability,
        }

    # ==================================================================================
    # BUILD FEATURES
    # ==================================================================================

    async def build_features(
        self,
        timestamp: datetime | None = None,
    ) -> dict:
        """
        Build all 45 inputs expected by the final V2 model.

        Output structure:

            {
                reference_hour_utc,
                prediction_target_hour_utc,
                feature_count,
                features
            }
        """

        reference_hour = (
            self.normalize_reference_hour(
                timestamp
            )
        )

        # ==================================================================================
        # LOAD 25-HOUR HISTORY
        # ==================================================================================

        history = (
            await self._load_hourly_history(
                reference_hour
            )
        )

        current = (
            history[
                0
            ]
        )

        # ==================================================================================
        # CURRENT HOUR FEATURES
        # ==================================================================================

        features = {
            "total_events":
                current[
                    "total_events"
                ],

            "arrivals":
                current[
                    "arrivals"
                ],

            "departures":
                current[
                    "departures"
                ],

            "unique_vessels":
                current[
                    "unique_vessels"
                ],

            # ==================================================================================
            # CURRENT TRAFFIC COMPOSITION
            # ==================================================================================

            "passenger_events":
                current[
                    "passenger_events"
                ],

            "cargo_events":
                current[
                    "cargo_events"
                ],

            "fishing_events":
                current[
                    "fishing_events"
                ],

            "tanker_events":
                current[
                    "tanker_events"
                ],

            "auxiliary_events":
                current[
                    "auxiliary_events"
                ],

            "tug_events":
                current[
                    "tug_events"
                ],

            # ==================================================================================
            # TOTAL EVENT LAGS
            # ==================================================================================

            "total_events_lag_1h":
                history[
                    1
                ][
                    "total_events"
                ],

            "total_events_lag_2h":
                history[
                    2
                ][
                    "total_events"
                ],

            "total_events_lag_3h":
                history[
                    3
                ][
                    "total_events"
                ],

            "total_events_lag_6h":
                history[
                    6
                ][
                    "total_events"
                ],

            "total_events_lag_24h":
                history[
                    24
                ][
                    "total_events"
                ],

            # ==================================================================================
            # ARRIVAL LAGS
            # ==================================================================================

            "arrivals_lag_1h":
                history[
                    1
                ][
                    "arrivals"
                ],

            "arrivals_lag_2h":
                history[
                    2
                ][
                    "arrivals"
                ],

            "arrivals_lag_3h":
                history[
                    3
                ][
                    "arrivals"
                ],

            "arrivals_lag_24h":
                history[
                    24
                ][
                    "arrivals"
                ],

            # ==================================================================================
            # DEPARTURE LAGS
            # ==================================================================================

            "departures_lag_1h":
                history[
                    1
                ][
                    "departures"
                ],

            "departures_lag_2h":
                history[
                    2
                ][
                    "departures"
                ],

            "departures_lag_3h":
                history[
                    3
                ][
                    "departures"
                ],

            "departures_lag_24h":
                history[
                    24
                ][
                    "departures"
                ],

            # ==================================================================================
            # UNIQUE VESSEL LAGS
            # ==================================================================================

            "unique_vessels_lag_1h":
                history[
                    1
                ][
                    "unique_vessels"
                ],

            "unique_vessels_lag_24h":
                history[
                    24
                ][
                    "unique_vessels"
                ],

            # ==================================================================================
            # TOTAL EVENT ROLLING MEANS
            # ==================================================================================

            "total_events_rolling_mean_3h":
                self._rolling_mean(
                    history=history,
                    field="total_events",
                    window=3,
                ),

            "total_events_rolling_mean_6h":
                self._rolling_mean(
                    history=history,
                    field="total_events",
                    window=6,
                ),

            "total_events_rolling_mean_24h":
                self._rolling_mean(
                    history=history,
                    field="total_events",
                    window=24,
                ),

            # ==================================================================================
            # ARRIVAL ROLLING MEANS
            # ==================================================================================

            "arrivals_rolling_mean_3h":
                self._rolling_mean(
                    history=history,
                    field="arrivals",
                    window=3,
                ),

            "arrivals_rolling_mean_6h":
                self._rolling_mean(
                    history=history,
                    field="arrivals",
                    window=6,
                ),

            "arrivals_rolling_mean_24h":
                self._rolling_mean(
                    history=history,
                    field="arrivals",
                    window=24,
                ),
        }

        # ==================================================================================
        # CALENDAR + CYCLICAL FEATURES
        # ==================================================================================

        features.update(
            self._calendar_features(
                reference_hour
            )
        )

        # ==================================================================================
        # MULTI-AREA CONTEXT
        # ==================================================================================

        features.update(
            {
                "centroid_lat":
                    STUDY_AREA_CENTROID_LAT,

                "centroid_lon":
                    STUDY_AREA_CENTROID_LON,

                "study_area":
                    STUDY_AREA,
            }
        )

        # ==================================================================================
        # VALIDATE FINAL MODEL CONTRACT
        # ==================================================================================

        missing = [
            feature
            for feature in FEATURE_COLUMNS
            if feature not in features
        ]

        extra = [
            feature
            for feature in features
            if feature not in FEATURE_COLUMNS
        ]

        if missing:
            raise RuntimeError(
                "Live feature builder is missing "
                "required ML features: "
                + ", ".join(
                    missing
                )
            )

        if extra:
            raise RuntimeError(
                "Live feature builder produced "
                "unexpected ML features: "
                + ", ".join(
                    extra
                )
            )

        # Exact same order expected by the production ML pipeline.
        ordered_features = {
            feature:
                features[
                    feature
                ]
            for feature in FEATURE_COLUMNS
        }

        return {
            "reference_hour_utc":
                reference_hour.isoformat(),

            "prediction_target_hour_utc":
                (
                    reference_hour
                    + timedelta(
                        hours=1
                    )
                ).isoformat(),

            "feature_count":
                len(
                    ordered_features
                ),

            "features":
                ordered_features,
        }


live_feature_builder = (
    LiveFeatureBuilder()
)