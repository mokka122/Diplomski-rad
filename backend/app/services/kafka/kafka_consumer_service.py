import asyncio
import logging

from app.kafka.consumer import (
    KafkaVesselConsumer,
)


logger = logging.getLogger(
    __name__
)


class KafkaConsumerService:
    """
    Background service wrapper around KafkaVesselConsumer.

    Responsibilities:

    - start the Kafka consumer
    - keep the consumer loop running
    - expose status to FastAPI
    - stop the consumer cleanly during application shutdown
    """

    def __init__(self):
        self.consumer = (
            KafkaVesselConsumer()
        )

        self._running = False

    # ==================================================================================
    # RUN
    # ==================================================================================

    async def run(self):
        logger.info(
            "Starting Kafka consumer service..."
        )

        self._running = True

        await self.consumer.start()

        try:
            await self.consumer.run()

        except asyncio.CancelledError:
            logger.info(
                "Kafka consumer service cancelled."
            )

            raise

        finally:
            self._running = False

            await self.consumer.stop()

            logger.info(
                "Kafka consumer service stopped."
            )

    # ==================================================================================
    # STOP
    # ==================================================================================

    async def stop(self):
        """
        Explicit shutdown hook used by FastAPI lifespan.

        The method is idempotent enough for application shutdown:
        KafkaVesselConsumer.stop() delegates to AIOKafkaConsumer.stop().
        """

        self._running = False

        try:
            await self.consumer.stop()

        except Exception:
            logger.exception(
                "Error while stopping Kafka consumer."
            )

    # ==================================================================================
    # STATUS
    # ==================================================================================

    def get_status(self) -> dict:
        status = (
            self.consumer
            .get_status()
        )

        status[
            "service_running"
        ] = self._running

        return status