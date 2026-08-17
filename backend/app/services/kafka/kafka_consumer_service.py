import asyncio
import logging

from app.kafka.consumer import KafkaVesselConsumer


logger = logging.getLogger(__name__)


class KafkaConsumerService:
    def __init__(self):
        self.consumer = KafkaVesselConsumer()

    async def run(self):
        logger.info("Starting Kafka consumer service...")

        await self.consumer.start()

        try:
            await self.consumer.run()

        except asyncio.CancelledError:
            logger.info("Kafka consumer service stopped.")
            raise

        finally:
            await self.consumer.stop()

    def get_status(self) -> dict:
        return self.consumer.get_status()