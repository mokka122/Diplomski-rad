import json
import os

from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv


load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

KAFKA_VESSEL_TOPIC = os.getenv(
    "KAFKA_VESSEL_TOPIC",
    "vessel-positions",
)


class KafkaVesselProducer:

    def __init__(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda value: json.dumps(
                value
            ).encode("utf-8"),
        )

    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def send_vessel(self, vessel):
        await self.producer.send_and_wait(
            KAFKA_VESSEL_TOPIC,
            vessel.model_dump(mode="json"),
        )