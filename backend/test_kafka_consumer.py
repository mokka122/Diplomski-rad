import asyncio

from app.kafka.consumer import KafkaVesselConsumer


async def main():
    consumer = KafkaVesselConsumer()

    await consumer.start()

    print("Kafka consumer started.")
    print("Waiting for messages...")

    try:
        await consumer.run()

    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())