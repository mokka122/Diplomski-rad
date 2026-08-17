import asyncio

from app.models.vessel import VesselPosition
from app.repositories.elasticsearch_vessel_repository import (
    ElasticsearchVesselRepository,
)


async def main():
    repository = ElasticsearchVesselRepository()

    try:
        await repository.create_index()

        vessel = VesselPosition(
            mmsi="TEST123456",
            vessel_name="OceanEye Elasticsearch Test Vessel",
            latitude=45.327,
            longitude=14.442,
            sog=12.5,
            cog=180.0,
            heading=178.0,
            timestamp="2026-08-11T17:30:00+00:00",
        )

        await repository.save_vessel(vessel)

        print(
            "Elasticsearch test document "
            "saved successfully."
        )

        count = await repository.count_documents()

        print(
            f"Documents in Elasticsearch index: {count}"
        )

    finally:
        await repository.close()


if __name__ == "__main__":
    asyncio.run(main())