from datetime import datetime, timezone

from app.db.redis import redis_client

from app.services.ais_ship_type_mapper import (
    map_ais_ship_type,
)

from app.services.traffic_event_service import (
    TrafficEvent,
    TrafficEventType,
)


class RedisTrafficRepository:
    """
    Stores short-lived live traffic aggregates.

    MongoDB:
        persistent traffic event history

    Redis:
        recent hourly aggregates used by dashboards
        and future ML inference
    """

    HOURLY_KEY_PREFIX = "traffic:hour:"
    VESSELS_KEY_PREFIX = "traffic:vessels:"

    # Keep seven days of live hourly data.
    #
    # This is currently enough for:
    #
    # - 1h / 2h / 3h lags
    # - 6h lag
    # - 24h lag
    # - rolling means
    # - frontend short-term history
    TTL_SECONDS = (
        7
        * 24
        * 60
        * 60
    )

    COUNTER_FIELDS = [
        "total_events",
        "arrivals",
        "departures",

        "passenger_events",
        "cargo_events",
        "fishing_events",
        "tanker_events",
        "auxiliary_events",
        "tug_events",
    ]

    # ==================================================================================
    # TIME
    # ==================================================================================

    def _normalize_hour(
        self,
        timestamp: datetime,
    ) -> datetime:

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

    def _hour_string(
        self,
        timestamp: datetime,
    ) -> str:

        hour = self._normalize_hour(
            timestamp
        )

        return hour.strftime(
            "%Y%m%d%H"
        )

    # ==================================================================================
    # REDIS KEYS
    # ==================================================================================

    def _hourly_key(
        self,
        timestamp: datetime,
    ) -> str:

        return (
            f"{self.HOURLY_KEY_PREFIX}"
            f"{self._hour_string(timestamp)}"
        )

    def _vessel_key(
        self,
        timestamp: datetime,
    ) -> str:

        return (
            f"{self.VESSELS_KEY_PREFIX}"
            f"{self._hour_string(timestamp)}"
        )

    # ==================================================================================
    # REGISTER EVENT
    # ==================================================================================

    async def register_event(
        self,
        event: TrafficEvent,
    ) -> None:

        hourly_key = self._hourly_key(
            event.timestamp
        )

        vessel_key = self._vessel_key(
            event.timestamp
        )

        # ----------------------------------------------------------------------------------
        # TOTAL EVENTS
        # ----------------------------------------------------------------------------------

        await redis_client.hincrby(
            hourly_key,
            "total_events",
            1,
        )

        # ----------------------------------------------------------------------------------
        # ARRIVAL / DEPARTURE PROXY
        # ----------------------------------------------------------------------------------

        if (
            event.event_type
            == TrafficEventType.ENTRY
        ):

            await redis_client.hincrby(
                hourly_key,
                "arrivals",
                1,
            )

        elif (
            event.event_type
            == TrafficEventType.EXIT
        ):

            await redis_client.hincrby(
                hourly_key,
                "departures",
                1,
            )

        # ----------------------------------------------------------------------------------
        # VESSEL GROUP
        # ----------------------------------------------------------------------------------

        group = map_ais_ship_type(
            event.ship_type
        )

        if group is not None:

            group_field = (
                f"{group}_events"
            )

            await redis_client.hincrby(
                hourly_key,
                group_field,
                1,
            )

        # ----------------------------------------------------------------------------------
        # UNIQUE VESSELS
        # ----------------------------------------------------------------------------------

        await redis_client.sadd(
            vessel_key,
            event.mmsi,
        )

        # ----------------------------------------------------------------------------------
        # ENSURE ALL EXPECTED FIELDS EXIST
        # ----------------------------------------------------------------------------------

        for field in self.COUNTER_FIELDS:

            await redis_client.hsetnx(
                hourly_key,
                field,
                0,
            )

        # ----------------------------------------------------------------------------------
        # TTL
        # ----------------------------------------------------------------------------------

        await redis_client.expire(
            hourly_key,
            self.TTL_SECONDS,
        )

        await redis_client.expire(
            vessel_key,
            self.TTL_SECONDS,
        )

    # ==================================================================================
    # GET HOUR
    # ==================================================================================

    async def get_hour(
        self,
        timestamp: datetime,
    ) -> dict:

        hour = self._normalize_hour(
            timestamp
        )

        hourly_key = self._hourly_key(
            hour
        )

        vessel_key = self._vessel_key(
            hour
        )

        values = await redis_client.hgetall(
            hourly_key
        )

        unique_vessels = (
            await redis_client.scard(
                vessel_key
            )
        )

        response = {
            "timestamp_utc":
                hour.isoformat(),

            "unique_vessels":
                int(
                    unique_vessels
                ),
        }

        for field in self.COUNTER_FIELDS:

            response[field] = int(
                values.get(
                    field,
                    0,
                )
            )

        return response

    # ==================================================================================
    # CURRENT HOUR
    # ==================================================================================

    async def get_current_hour(
        self,
    ) -> dict:

        return await self.get_hour(
            datetime.now(
                timezone.utc
            )
        )

    # ==================================================================================
    # MULTIPLE HOURS
    # ==================================================================================

    async def get_hours(
        self,
        timestamps: list[datetime],
    ) -> list[dict]:

        results = []

        for timestamp in timestamps:

            results.append(
                await self.get_hour(
                    timestamp
                )
            )

        return results
    
    # ==================================================================================
    # INITIALIZE / SNAPSHOT HOUR
    # ==================================================================================

    async def ensure_hour(
        self,
        timestamp: datetime,
    ) -> bool:
        """
        Ensure that an hourly traffic hash exists even when
        no ENTRY / EXIT events occurred during that hour.

        This is critical for distinguishing:

            known zero traffic
                from
            missing historical data

        Returns:
            True  -> hour was newly initialized
            False -> hour already existed
        """

        hour = self._normalize_hour(
            timestamp
        )

        hourly_key = self._hourly_key(
            hour
        )

        existed_before = bool(
            await redis_client.exists(
                hourly_key
            )
        )

        for field in self.COUNTER_FIELDS:

            await redis_client.hsetnx(
                hourly_key,
                field,
                0,
            )

        await redis_client.expire(
            hourly_key,
            self.TTL_SECONDS,
        )

        return not existed_before
    
    # ==================================================================================
    # CHECK WHETHER HOUR EXISTS
    # ==================================================================================

    async def hour_exists(
        self,
        timestamp: datetime,
    ) -> bool:

        hourly_key = self._hourly_key(
            timestamp
        )

        exists = await redis_client.exists(
            hourly_key
        )

        return bool(
            exists
        )

    # ==================================================================================
    # DELETE TEST DATA
    # ==================================================================================

    async def delete_hour(
        self,
        timestamp: datetime,
    ) -> None:

        await redis_client.delete(
            self._hourly_key(
                timestamp
            )
        )

        await redis_client.delete(
            self._vessel_key(
                timestamp
            )
        )