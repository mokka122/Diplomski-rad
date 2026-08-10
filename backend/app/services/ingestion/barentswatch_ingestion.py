import asyncio
import logging

from app.repositories.vessel_repository import VesselRepository
from app.services.data_providers.barentswatch import BarentsWatchProvider
from app.services.normalizer import normalize_barentswatch_message


logger = logging.getLogger(__name__)


class BarentsWatchIngestionService:
    RECONNECT_DELAY_SECONDS = 5

    def __init__(self):
        self.provider = BarentsWatchProvider()
        self.repository = VesselRepository()

        self.received_messages = 0
        self.saved_positions = 0
        self.updated_current_state = 0
        self.skipped_messages = 0

    async def run(self):
        while True:
            try:
                logger.info("Connecting to BarentsWatch AIS stream...")

                async for raw_message in self.provider.stream_messages():
                    self.received_messages += 1

                    try:
                        position = normalize_barentswatch_message(raw_message)

                        position_saved = await self.repository.save_position(
                            position
                        )
                        current_updated = (
                            await self.repository.upsert_current_vessel(
                                position
                            )
                        )

                        if position_saved:
                            self.saved_positions += 1

                        if current_updated:
                            self.updated_current_state += 1

                    except Exception as error:
                        self.skipped_messages += 1
                        logger.warning(
                            "Skipping invalid AIS message: %s",
                            error,
                        )

            except asyncio.CancelledError:
                logger.info("BarentsWatch ingestion stopped.")
                raise

            except Exception:
                logger.exception(
                    "BarentsWatch connection failed. "
                    "Retrying in %s seconds...",
                    self.RECONNECT_DELAY_SECONDS,
                )

            await asyncio.sleep(self.RECONNECT_DELAY_SECONDS)

    def get_status(self) -> dict:
        return {
            "received_messages": self.received_messages,
            "saved_positions": self.saved_positions,
            "updated_current_state": self.updated_current_state,
            "skipped_messages": self.skipped_messages,
        }