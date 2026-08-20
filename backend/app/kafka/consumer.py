import json
import os

from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

from app.models.vessel import VesselPosition

from app.repositories.elasticsearch_vessel_repository import (
    ElasticsearchVesselRepository,
)

from app.repositories.redis_traffic_repository import (
    RedisTrafficRepository,
)

from app.repositories.redis_vessel_repository import (
    RedisVesselRepository,
)

from app.repositories.traffic_event_repository import (
    TrafficEventRepository,
)

from app.repositories.vessel_repository import (
    VesselRepository,
)

from app.services.traffic_event_service import (
    traffic_event_service,
)


load_dotenv()


# ======================================================================================
# KAFKA CONFIGURATION
# ======================================================================================

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

KAFKA_VESSEL_TOPIC = os.getenv(
    "KAFKA_VESSEL_TOPIC",
    "vessel-positions",
)

KAFKA_CONSUMER_GROUP = os.getenv(
    "KAFKA_CONSUMER_GROUP",
    "oceaneye-vessel-processor",
)


class KafkaVesselConsumer:

    def __init__(self):
        # ==================================================================================
        # KAFKA
        # ==================================================================================

        self.consumer = AIOKafkaConsumer(
            KAFKA_VESSEL_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        # ==================================================================================
        # EXISTING STORAGE
        # ==================================================================================

        self.repository = (
            VesselRepository()
        )

        self.redis_repository = (
            RedisVesselRepository()
        )

        self.elasticsearch_repository = (
            ElasticsearchVesselRepository()
        )

        # ==================================================================================
        # TRAFFIC EVENT STORAGE
        # ==================================================================================

        self.traffic_event_repository = (
            TrafficEventRepository()
        )

        self.redis_traffic_repository = (
            RedisTrafficRepository()
        )

        # ==================================================================================
        # COUNTERS
        # ==================================================================================

        self.processed_messages = 0
        self.failed_messages = 0

        self.detected_traffic_events = 0
        self.saved_traffic_events = 0

    # ==================================================================================
    # START / STOP
    # ==================================================================================

    async def start(self):
        await self.consumer.start()

    async def stop(self):
        await self.consumer.stop()

    # ==================================================================================
    # TRAFFIC EVENT PROCESSING
    # ==================================================================================

    async def _process_traffic_event(
        self,
        position: VesselPosition,
    ) -> None:
        """
        Send the latest vessel position through the Ålesund
        geofence transition detector.

        Most AIS messages produce no traffic event.

        Only:

            outside -> inside

        or:

            inside -> outside

        generates an event.
        """

        event = (
            traffic_event_service
            .process_position(
                position.model_dump()
            )
        )

        if event is None:
            return

        self.detected_traffic_events += 1

        # ----------------------------------------------------------------------------------
        # MongoDB is the historical source of truth.
        # ----------------------------------------------------------------------------------

        inserted = (
            await self
            .traffic_event_repository
            .save_event(
                event
            )
        )

        # ----------------------------------------------------------------------------------
        # Only increment Redis counters if this MongoDB event
        # was actually new.
        #
        # This prevents duplicate Kafka processing from inflating
        # the hourly counters.
        # ----------------------------------------------------------------------------------

        if inserted:
            self.saved_traffic_events += 1

            await (
                self.redis_traffic_repository
                .register_event(
                    event
                )
            )

        print(
            f"Ålesund traffic event detected: "
            f"{event.event_type.value} | "
            f"MMSI={event.mmsi} | "
            f"new={inserted}"
        )

    # ==================================================================================
    # RUN
    # ==================================================================================

    async def run(self):
        async for message in self.consumer:
            try:
                print(
                    f"Kafka message received: "
                    f"topic={message.topic}, "
                    f"partition={message.partition}, "
                    f"offset={message.offset}"
                )

                data = json.loads(
                    message.value.decode(
                        "utf-8"
                    )
                )

                print(
                    f"Kafka message data: "
                    f"{data}"
                )

                # ----------------------------------------------------------------------------------
                # Validate normalized Kafka payload.
                # ----------------------------------------------------------------------------------

                position = (
                    VesselPosition.model_validate(
                        data
                    )
                )

                # ==================================================================================
                # EXISTING OCEANEYE PIPELINE
                #
                # DO NOT REMOVE OR REORDER THESE WRITES.
                # ==================================================================================

                await (
                    self.repository
                    .save_position(
                        position
                    )
                )

                await (
                    self.repository
                    .upsert_current_vessel(
                        position
                    )
                )

                await (
                    self.redis_repository
                    .save_current_vessel(
                        position
                    )
                )

                await (
                    self.elasticsearch_repository
                    .save_vessel(
                        position
                    )
                )

                # ==================================================================================
                # NEW ÅLESUND TRAFFIC PIPELINE
                # ==================================================================================

                await self._process_traffic_event(
                    position
                )

                # ==================================================================================
                # COMPLETE
                # ==================================================================================

                self.processed_messages += 1

                print(
                    f"Vessel {position.mmsi} "
                    f"processed successfully."
                )

            except Exception as error:
                self.failed_messages += 1

                print(
                    f"Failed to process Kafka message: "
                    f"{error}"
                )

    # ==================================================================================
    # STATUS
    # ==================================================================================

    def get_status(self) -> dict:
        traffic_status = (
            traffic_event_service
            .get_status()
        )

        return {
            "processed_messages":
                self.processed_messages,

            "failed_messages":
                self.failed_messages,

            "detected_traffic_events":
                self.detected_traffic_events,

            "saved_traffic_events":
                self.saved_traffic_events,

            "tracked_geofence_vessels":
                traffic_status[
                    "tracked_vessels"
                ],

            "vessels_inside_alesund":
                traffic_status[
                    "vessels_inside"
                ],

            "entries_detected":
                traffic_status[
                    "entries_detected"
                ],

            "exits_detected":
                traffic_status[
                    "exits_detected"
                ],
        }