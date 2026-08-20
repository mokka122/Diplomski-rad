import math

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from zoneinfo import ZoneInfo

from app.ml.config import (
    FEATURE_COLUMNS,
)

from app.repositories.redis_traffic_repository import (
    RedisTrafficRepository,
)


OSLO_TIMEZONE = ZoneInfo(
    "Europe/Oslo"
)


class LiveFeatureBuilder:
    """
    Builds the same 42-feature structure used by the
    historical OceanEye ML dataset.

    Historical source:
        SafeSeaNet voyages

    Live source:
        BarentsWatch AIS
        -> geofence ENTRY / EXIT
        -> Redis hourly aggregates

    The semantic mapping is approximate but intentionally
    kept structurally compatible with the ML dataset.
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

        return timestamp.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

    # ==================================================================================
    # LOAD HISTORY
    # ==================================================================================

    async def _load_hourly_history(
        self,
        reference_hour: datetime,
    ) -> dict[int, dict]:
        """
        Load reference hour and previous 24 hours.

        Dictionary keys represent lag:

            0  = current/reference hour
            1  = previous hour
            2  = two hours ago
            ...
            24 = same hour previous day
        """

        history = {}

        for lag in range(
            0,
            25,
        ):

            timestamp = (
                reference_hour
                - timedelta(
                    hours=lag
                )
            )

            history[lag] = (
                await self.redis_repository
                .get_hour(
                    timestamp
                )
            )

        return history

    # ==================================================================================
    # ROLLING
    # ==================================================================================

    def _rolling_mean(
        self,
        history: dict[int, dict],
        field: str,
        window: int,
    ) -> float:
        """
        Historical training code used:

            series.shift(1).rolling(window)

        Therefore live rolling means MUST NOT use lag 0.

        For a 3-hour rolling feature:

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

            values.append(
                float(
                    hour.get(
                        field,
                        0,
                    )
                )
            )

        if not values:
            return 0.0

        return float(
            sum(values)
            / len(values)
        )

    # ==================================================================================
    # CALENDAR
    # ==================================================================================

    def _calendar_features(
        self,
        reference_hour: datetime,
    ) -> dict:

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

        reference_hour = (
            self.normalize_reference_hour(
                timestamp
            )
        )

        required_lags = [
            0,
            1,
            2,
            3,
            6,
            24,
        ]

        availability = {}

        for lag in required_lags:

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
                    exists,
            }

        available_count = sum(
            1
            for value
            in availability.values()
            if value[
                "available"
            ]
        )

        required_count = len(
            required_lags
        )

        return {
            "ready":
                available_count
                == required_count,

            "available_required_hours":
                available_count,

            "required_hours":
                required_count,

            "availability":
                availability,
        }

    # ==================================================================================
    # BUILD
    # ==================================================================================

    async def build_features(
        self,
        timestamp: datetime | None = None,
    ) -> dict:

        reference_hour = (
            self.normalize_reference_hour(
                timestamp
            )
        )

        history = (
            await self._load_hourly_history(
                reference_hour
            )
        )

        current = history[0]

        features = {
            # ==================================================================================
            # CURRENT HOUR
            # ==================================================================================

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
                history[1][
                    "total_events"
                ],

            "total_events_lag_2h":
                history[2][
                    "total_events"
                ],

            "total_events_lag_3h":
                history[3][
                    "total_events"
                ],

            "total_events_lag_6h":
                history[6][
                    "total_events"
                ],

            "total_events_lag_24h":
                history[24][
                    "total_events"
                ],

            # ==================================================================================
            # ARRIVAL LAGS
            # ==================================================================================

            "arrivals_lag_1h":
                history[1][
                    "arrivals"
                ],

            "arrivals_lag_2h":
                history[2][
                    "arrivals"
                ],

            "arrivals_lag_3h":
                history[3][
                    "arrivals"
                ],

            "arrivals_lag_24h":
                history[24][
                    "arrivals"
                ],

            # ==================================================================================
            # DEPARTURE LAGS
            # ==================================================================================

            "departures_lag_1h":
                history[1][
                    "departures"
                ],

            "departures_lag_2h":
                history[2][
                    "departures"
                ],

            "departures_lag_3h":
                history[3][
                    "departures"
                ],

            "departures_lag_24h":
                history[24][
                    "departures"
                ],

            # ==================================================================================
            # UNIQUE VESSELS
            # ==================================================================================

            "unique_vessels_lag_1h":
                history[1][
                    "unique_vessels"
                ],

            "unique_vessels_lag_24h":
                history[24][
                    "unique_vessels"
                ],

            # ==================================================================================
            # ROLLING TOTAL EVENTS
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
            # ROLLING ARRIVALS
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
        # VALIDATE FEATURE CONTRACT
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

        # Exact same ordering as ML runtime contract.
        ordered_features = {
            feature:
                features[feature]
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