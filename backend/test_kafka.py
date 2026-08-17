import asyncio

from app.kafka.producer import KafkaVesselProducer
from app.models.vessel import VesselPosition


async def main():
    producer = KafkaVesselProducer()

    await producer.start()

    try:
        vessel = VesselPosition(
            mmsi="TEST123456",
            vessel_name="OceanEye Test Vessel",
            latitude=45.327,
            longitude=14.442,
            sog=12.5,
            cog=180.0,
            heading=178.0,
            timestamp="2026-08-11T17:30:00+00:00",
        )

        await producer.send_vessel(vessel)

        print("Kafka test message sent successfully.")

    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())