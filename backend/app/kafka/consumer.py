import json
import logging
import os

from aiokafka import (
    AIOKafkaConsumer,
)

from dotenv import (
    load_dotenv,
)

from app.models.vessel import (
    VesselPosition,
)

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


logger = logging.getLogger(
    __name__
)


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


# ======================================================================================
# BATCH CONFIGURATION
# ======================================================================================

KAFKA_BATCH_SIZE = int(
    os.getenv(
        "KAFKA_BATCH_SIZE",
        "250",
    )
)

KAFKA_BATCH_TIMEOUT_MS = int(
    os.getenv(
        "KAFKA_BATCH_TIMEOUT_MS",
        "1000",
    )
)


class KafkaVesselConsumer:

    def __init__(self):

        # ==================================================================================
        # KAFKA
        # ==================================================================================

        self.consumer = (
            AIOKafkaConsumer(
                KAFKA_VESSEL_TOPIC,
                bootstrap_servers=(
                    KAFKA_BOOTSTRAP_SERVERS
                ),
                group_id=(
                    KAFKA_CONSUMER_GROUP
                ),
                auto_offset_reset="earliest",

                # Preserve the project's existing delivery behaviour.
                # We are changing batching, not offset semantics.
                enable_auto_commit=True,
            )
        )

        # ==================================================================================
        # STORAGE
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
        # TRAFFIC
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

        self.processed_batches = 0

        self.last_batch_size = 0

        self.last_error = None

        self.last_error_stage = None

        self.last_error_mmsi = None

    # ==================================================================================
    # START / STOP
    # ==================================================================================

    async def start(self):
        await self.consumer.start()

        logger.info(
            "Kafka vessel consumer started. "
            "batch_size=%s batch_timeout_ms=%s",
            KAFKA_BATCH_SIZE,
            KAFKA_BATCH_TIMEOUT_MS,
        )

    async def stop(self):
        await self.consumer.stop()

        await (
            self.elasticsearch_repository
            .close()
        )

        logger.info(
            "Kafka vessel consumer stopped."
        )

    # ==================================================================================
    # FAILURE TRACKING
    # ==================================================================================

    def _record_failure(
        self,
        *,
        stage: str,
        error: Exception,
        mmsi: str | None = None,
        count: int = 1,
    ) -> None:

        self.failed_messages += (
            count
        )

        self.last_error = (
            str(error)
        )

        self.last_error_stage = (
            stage
        )

        self.last_error_mmsi = (
            str(mmsi)
            if mmsi is not None
            else None
        )

        logger.exception(
            "Kafka vessel processing failed "
            "| stage=%s "
            "| MMSI=%s "
            "| affected_messages=%s",
            stage,
            mmsi,
            count,
        )

    # ==================================================================================
    # TRAFFIC EVENT
    # ==================================================================================

    async def _process_traffic_event(
        self,
        position: VesselPosition,
    ) -> None:
        """
        Process one normalized AIS position through the
        OceanEye study-area transition detector.

        Only a real boundary transition creates an event:

            outside -> inside = ENTRY
            inside  -> outside = EXIT
        """

        event = (
            await traffic_event_service
            .process_position(
                position.model_dump()
            )
        )

        if event is None:
            return

        self.detected_traffic_events += 1

        # ----------------------------------------------------------------------------------
        # MongoDB is the persistent source of truth.
        # ----------------------------------------------------------------------------------

        inserted = (
            await self
            .traffic_event_repository
            .save_event(
                event
            )
        )

        # ----------------------------------------------------------------------------------
        # Only newly inserted events may increment Redis.
        # ----------------------------------------------------------------------------------

        if inserted:

            self.saved_traffic_events += 1

            await (
                self.redis_traffic_repository
                .register_event(
                    event
                )
            )

        logger.info(
            "Traffic event detected: "
            "%s | MMSI=%s | new=%s",
            event.event_type.value,
            event.mmsi,
            inserted,
        )

    # ==================================================================================
    # GET KAFKA BATCH
    # ==================================================================================

    async def _get_batch(
        self,
    ):
        """
        Fetch up to KAFKA_BATCH_SIZE records.

        getmany() prevents the consumer from paying the full MongoDB
        network/write overhead separately for every AIS message.
        """

        records = (
            await self.consumer.getmany(
                timeout_ms=(
                    KAFKA_BATCH_TIMEOUT_MS
                ),
                max_records=(
                    KAFKA_BATCH_SIZE
                ),
            )
        )

        messages = []

        # Preserve Kafka partition order.
        for topic_partition in sorted(
            records.keys(),
            key=lambda item: (
                item.topic,
                item.partition,
            ),
        ):
            partition_messages = (
                records[
                    topic_partition
                ]
            )

            messages.extend(
                partition_messages
            )

        return messages

    # ==================================================================================
    # DECODE / VALIDATE BATCH
    # ==================================================================================

    def _decode_batch(
        self,
        messages,
    ):
        """
        Decode and validate Kafka records individually.

        A malformed AIS record must not invalidate the entire batch.
        """

        valid_items = []

        for message in messages:

            stage = (
                "decode_kafka_message"
            )

            mmsi = None

            try:

                # ------------------------------------------------------------------------------
                # Decode JSON
                # ------------------------------------------------------------------------------

                data = json.loads(
                    message.value.decode(
                        "utf-8"
                    )
                )

                mmsi = (
                    data.get(
                        "mmsi"
                    )
                )

                # ------------------------------------------------------------------------------
                # Pydantic validation
                # ------------------------------------------------------------------------------

                stage = (
                    "validate_vessel_position"
                )

                position = (
                    VesselPosition.model_validate(
                        data
                    )
                )

                valid_items.append(
                    (
                        message,
                        position,
                    )
                )

            except Exception as error:

                self._record_failure(
                    stage=stage,
                    error=error,
                    mmsi=(
                        str(mmsi)
                        if mmsi is not None
                        else None
                    ),
                )

        return valid_items

    # ==================================================================================
    # PROCESS NON-MONGO STAGES
    # ==================================================================================

    async def _process_post_mongo_stages(
        self,
        message,
        position: VesselPosition,
    ) -> bool:
        """
        Redis, Elasticsearch and geofence processing remain ordered
        per Kafka message.

        This intentionally preserves ENTRY / EXIT transition semantics.
        """

        stage = (
            "redis_save_current_vessel"
        )

        try:

            # ------------------------------------------------------------------------------
            # REDIS - CURRENT VESSEL
            # ------------------------------------------------------------------------------

            await (
                self.redis_repository
                .save_current_vessel(
                    position
                )
            )

            # ------------------------------------------------------------------------------
            # ELASTICSEARCH
            # ------------------------------------------------------------------------------

            stage = (
                "elasticsearch_save_vessel"
            )

            await (
                self.elasticsearch_repository
                .save_vessel(
                    position
                )
            )

            # ------------------------------------------------------------------------------
            # TRAFFIC EVENT DETECTION
            # ------------------------------------------------------------------------------

            stage = (
                "traffic_event_processing"
            )

            await (
                self._process_traffic_event(
                    position
                )
            )

            return True

        except Exception as error:

            self._record_failure(
                stage=stage,
                error=error,
                mmsi=position.mmsi,
            )

            logger.error(
                "Failed Kafka record metadata "
                "| topic=%s "
                "| partition=%s "
                "| offset=%s",
                message.topic,
                message.partition,
                message.offset,
            )

            return False

    # ==================================================================================
    # RUN
    # ==================================================================================

    async def run(self):
        """
        Consume vessel positions from Kafka using controlled batching.

        MongoDB history and current-state writes are batched because Atlas
        network/write latency was measured as the main throughput bottleneck.

        Redis, Elasticsearch and geofence processing remain sequential so
        vessel transition order is preserved.
        """

        while True:

            # ==================================================================================
            # FETCH BATCH
            # ==================================================================================

            messages = (
                await self._get_batch()
            )

            if not messages:
                continue

            # ==================================================================================
            # DECODE / VALIDATE
            # ==================================================================================

            valid_items = (
                self._decode_batch(
                    messages
                )
            )

            if not valid_items:
                continue

            positions = [
                position
                for (
                    _,
                    position,
                )
                in valid_items
            ]

            self.last_batch_size = (
                len(
                    positions
                )
            )

            # ==================================================================================
            # MONGODB - BULK HISTORY
            # ==================================================================================

            stage = (
                "mongodb_save_positions_bulk"
            )

            try:

                await (
                    self.repository
                    .save_positions_bulk(
                        positions
                    )
                )

                # ==================================================================================
                # MONGODB - BULK CURRENT STATE
                # ==================================================================================

                stage = (
                    "mongodb_upsert_current_vessels_bulk"
                )

                await (
                    self.repository
                    .upsert_current_vessels_bulk(
                        positions
                    )
                )

            except Exception as error:

                self._record_failure(
                    stage=stage,
                    error=error,
                    count=len(
                        valid_items
                    ),
                )

                # MongoDB persistence is foundational for this batch.
                # Do not continue into Redis / Elasticsearch / geofence when
                # the MongoDB batch itself failed.
                continue

            # ==================================================================================
            # REDIS / ELASTICSEARCH / GEOFENCE
            # ==================================================================================

            for (
                message,
                position,
            ) in valid_items:

                success = (
                    await self
                    ._process_post_mongo_stages(
                        message,
                        position,
                    )
                )

                if not success:
                    continue

                self.processed_messages += 1

                self.last_error = None

                self.last_error_stage = None

                self.last_error_mmsi = None

            # ==================================================================================
            # BATCH COMPLETE
            # ==================================================================================

            self.processed_batches += 1

            if (
                self.processed_batches
                % 10
                == 0
            ):
                logger.info(
                    "Kafka batch processing status: "
                    "batches=%s "
                    "last_batch=%s "
                    "processed=%s "
                    "failed=%s",
                    self.processed_batches,
                    self.last_batch_size,
                    self.processed_messages,
                    self.failed_messages,
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

            "processed_batches":
                self.processed_batches,

            "last_batch_size":
                self.last_batch_size,

            "configured_batch_size":
                KAFKA_BATCH_SIZE,

            "batch_timeout_ms":
                KAFKA_BATCH_TIMEOUT_MS,

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

            "last_error_stage":
                self.last_error_stage,

            "last_error_mmsi":
                self.last_error_mmsi,

            "last_error":
                self.last_error,
        }