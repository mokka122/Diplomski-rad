import json
import os

from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

from app.models.vessel import VesselPosition
from app.repositories.redis_vessel_repository import (
    RedisVesselRepository,
)
from app.repositories.vessel_repository import VesselRepository
from app.repositories.elasticsearch_vessel_repository import (
    ElasticsearchVesselRepository,
)

load_dotenv()


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
        self.consumer = AIOKafkaConsumer(
            KAFKA_VESSEL_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        self.repository = VesselRepository()
        
        self.redis_repository = RedisVesselRepository()
        self.elasticsearch_repository = (
        ElasticsearchVesselRepository()
        )

        self.processed_messages = 0
        self.failed_messages = 0
        

    async def start(self):
        await self.consumer.start()

    async def stop(self):
        await self.consumer.stop()

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
                    message.value.decode("utf-8")
                )

                print(
                    f"Kafka message data: {data}"
                )

                position = VesselPosition.model_validate(data)

                await self.repository.save_position(
                    position
                )

                await self.repository.upsert_current_vessel(
                    position
                )

                await self.redis_repository.save_current_vessel(
                    position
                )
                
                await self.elasticsearch_repository.save_vessel(
                    position
                )

                self.processed_messages += 1

                print(
                    f"Vessel {position.mmsi} "
                    f"processed successfully."
                )

            except Exception as error:
                self.failed_messages += 1

                print(
                    f"Failed to process Kafka message: {error}"
                )
    
    def get_status(self) -> dict:
        return {
            "processed_messages": self.processed_messages,
            "failed_messages": self.failed_messages,
        }