import asyncio
import logging

from app.kafka.producer import KafkaVesselProducer
from app.services.data_providers.barentswatch import BarentsWatchProvider
from app.services.normalizer import normalize_barentswatch_message


logger = logging.getLogger(__name__)


class BarentsWatchIngestionService:
    RECONNECT_DELAY_SECONDS = 5

    def __init__(self):
        self.provider = BarentsWatchProvider()
        self.kafka_producer = KafkaVesselProducer()

        self.received_messages = 0
        self.sent_to_kafka = 0
        self.skipped_messages = 0

    async def run(self):
        await self.kafka_producer.start()

        try:
            while True:
                try:
                    logger.info(
                        "Connecting to BarentsWatch AIS stream..."
                    )

                    async for raw_message in self.provider.stream_messages():
                        self.received_messages += 1

                        try:
                            position = normalize_barentswatch_message(
                                raw_message
                            )

                            await self.kafka_producer.send_vessel(
                                position
                            )

                            self.sent_to_kafka += 1

                        except Exception as error:
                            self.skipped_messages += 1

                            logger.warning(
                                "Skipping invalid AIS message: %s",
                                error,
                            )

                except asyncio.CancelledError:
                    logger.info(
                        "BarentsWatch ingestion stopped."
                    )
                    raise

                except Exception:
                    logger.exception(
                        "BarentsWatch connection failed. "
                        "Retrying in %s seconds...",
                        self.RECONNECT_DELAY_SECONDS,
                    )

                await asyncio.sleep(
                    self.RECONNECT_DELAY_SECONDS
                )

        finally:
            await self.kafka_producer.stop()

    def get_status(self) -> dict:
        return {
            "received_messages": self.received_messages,
            "sent_to_kafka": self.sent_to_kafka,
            "skipped_messages": self.skipped_messages,
        }