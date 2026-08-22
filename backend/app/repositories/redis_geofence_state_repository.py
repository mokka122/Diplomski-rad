from datetime import (
    datetime,
    timezone,
)

from app.db.redis import (
    redis_client,
)


class RedisGeofenceStateRepository:
    """
    Stores the latest known OceanEye geofence state for each vessel.

    Purpose:

    - preserve INSIDE / OUTSIDE state across FastAPI restarts
    - avoid reinitializing every vessel after each restart
    - prevent losing boundary-transition context

    A TTL is intentionally used.

    If OceanEye has not observed a vessel for a long period,
    its old geofence state should expire rather than creating
    a potentially false ENTRY / EXIT event from stale data.
    """

    KEY_PREFIX = (
        "traffic:geofence:"
    )

    # Keep vessel boundary state for 24 hours.
    #
    # This comfortably survives normal development restarts while
    # preventing very old vessel positions from generating false
    # transitions after a long system outage.
    TTL_SECONDS = (
        24
        * 60
        * 60
    )

    # ==================================================================================
    # KEY
    # ==================================================================================

    def _key(
        self,
        mmsi: str,
    ) -> str:

        return (
            f"{self.KEY_PREFIX}"
            f"{mmsi}"
        )

    # ==================================================================================
    # SAVE
    # ==================================================================================

    async def save_state(
        self,
        mmsi: str,
        inside: bool,
        last_timestamp: datetime,
        latitude: float,
        longitude: float,
    ) -> None:

        if last_timestamp.tzinfo is None:

            last_timestamp = (
                last_timestamp.replace(
                    tzinfo=timezone.utc
                )
            )

        last_timestamp = (
            last_timestamp.astimezone(
                timezone.utc
            )
        )

        key = (
            self._key(
                mmsi
            )
        )

        await redis_client.hset(
            key,
            mapping={
                "inside":
                    "1"
                    if inside
                    else "0",

                "last_timestamp":
                    last_timestamp.isoformat(),

                "latitude":
                    str(latitude),

                "longitude":
                    str(longitude),
            },
        )

        await redis_client.expire(
            key,
            self.TTL_SECONDS,
        )

    # ==================================================================================
    # GET
    # ==================================================================================

    async def get_state(
        self,
        mmsi: str,
    ) -> dict | None:

        key = (
            self._key(
                mmsi
            )
        )

        values = (
            await redis_client.hgetall(
                key
            )
        )

        if not values:
            return None

        try:

            inside_raw = (
                values.get(
                    "inside"
                )
            )

            timestamp_raw = (
                values.get(
                    "last_timestamp"
                )
            )

            latitude_raw = (
                values.get(
                    "latitude"
                )
            )

            longitude_raw = (
                values.get(
                    "longitude"
                )
            )

            if (
                timestamp_raw is None
                or latitude_raw is None
                or longitude_raw is None
            ):
                return None

            timestamp = (
                datetime.fromisoformat(
                    timestamp_raw
                )
            )

            if timestamp.tzinfo is None:

                timestamp = timestamp.replace(
                    tzinfo=timezone.utc
                )

            else:

                timestamp = (
                    timestamp.astimezone(
                        timezone.utc
                    )
                )

            return {
                "inside":
                    inside_raw
                    in (
                        "1",
                        1,
                        True,
                        "true",
                        "True",
                    ),

                "last_timestamp":
                    timestamp,

                "latitude":
                    float(
                        latitude_raw
                    ),

                "longitude":
                    float(
                        longitude_raw
                    ),
            }

        except (
            TypeError,
            ValueError,
        ):

            return None

    # ==================================================================================
    # DELETE
    # ==================================================================================

    async def delete_state(
        self,
        mmsi: str,
    ) -> None:

        await redis_client.delete(
            self._key(
                mmsi
            )
        )