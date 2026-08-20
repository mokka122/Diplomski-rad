import asyncio
import logging

from datetime import (
    datetime,
    timezone,
)

from app.repositories.redis_traffic_repository import (
    RedisTrafficRepository,
)


logger = logging.getLogger(
    __name__
)


class HourlyTrafficSnapshotService:
    """
    Ensures that every hour observed while OceanEye is running
    has an explicit Redis traffic record.

    Example:

        traffic:hour:2026081718

        total_events      = 0
        arrivals          = 0
        departures        = 0
        passenger_events  = 0
        ...

    even if no traffic event occurred.

    This allows OceanEye to distinguish:

        hour exists + counters == 0
            -> known zero traffic

        hour does not exist
            -> missing historical observation
    """

    CHECK_INTERVAL_SECONDS = 30

    def __init__(self):
        self.redis_repository = (
            RedisTrafficRepository()
        )

        self._running = False

        self.check_count = 0

        self.initialized_hours = 0

        self.last_checked_at = None

        self.last_observed_hour = None

        self.last_error = None

    # ==================================================================================
    # SINGLE CHECK
    # ==================================================================================

    async def ensure_current_hour(
        self,
        timestamp: datetime | None = None,
    ) -> bool:
        """
        Ensure that the current UTC hour exists in Redis.

        Can also accept a timestamp for testing.
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

        hour = timestamp.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        created = (
            await self.redis_repository
            .ensure_hour(
                hour
            )
        )

        self.check_count += 1

        self.last_checked_at = (
            datetime.now(
                timezone.utc
            )
        )

        self.last_observed_hour = (
            hour
        )

        self.last_error = None

        if created:

            self.initialized_hours += 1

            logger.info(
                "Initialized empty traffic snapshot "
                "for hour %s",
                hour.isoformat(),
            )

        return created

    # ==================================================================================
    # BACKGROUND LOOP
    # ==================================================================================

    async def run(self):
        """
        Background loop used by FastAPI lifespan.

        Checks every 30 seconds whether the current
        hourly Redis snapshot exists.
        """

        logger.info(
            "Starting hourly traffic snapshot service..."
        )

        self._running = True

        try:

            while True:

                try:

                    await self.ensure_current_hour()

                except asyncio.CancelledError:

                    raise

                except Exception as error:

                    self.last_error = str(
                        error
                    )

                    logger.exception(
                        "Hourly traffic snapshot "
                        "check failed."
                    )

                await asyncio.sleep(
                    self.CHECK_INTERVAL_SECONDS
                )

        except asyncio.CancelledError:

            logger.info(
                "Hourly traffic snapshot "
                "service stopped."
            )

            raise

        finally:

            self._running = False

    # ==================================================================================
    # STATUS
    # ==================================================================================

    def get_status(self) -> dict:

        return {
            "running":
                self._running,

            "check_interval_seconds":
                self.CHECK_INTERVAL_SECONDS,

            "check_count":
                self.check_count,

            "initialized_hours":
                self.initialized_hours,

            "last_checked_at": (
                self.last_checked_at.isoformat()
                if self.last_checked_at
                else None
            ),

            "last_observed_hour": (
                self.last_observed_hour.isoformat()
                if self.last_observed_hour
                else None
            ),

            "last_error":
                self.last_error,
        }


hourly_traffic_snapshot_service = (
    HourlyTrafficSnapshotService()
)