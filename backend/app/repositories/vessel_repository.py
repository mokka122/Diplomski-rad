from datetime import datetime, timezone

from app.db.database import database
from app.models.vessel import VesselPosition


class VesselRepository:

    async def save_position(self, position: VesselPosition):
        document = position.model_dump()

        result = await database["vessel_positions"].update_one(
            {
                "mmsi": position.mmsi,
                "timestamp": position.timestamp,
            },
            {
                "$setOnInsert": document,
            },
            upsert=True,
        )

        return result.upserted_id is not None

    async def upsert_current_vessel(self, position: VesselPosition):
        collection = database["vessels"]

        current_vessel = await collection.find_one(
            {
                "mmsi": position.mmsi,
            }
        )

        if current_vessel is not None:
            current_timestamp = current_vessel.get("timestamp")

            if current_timestamp is not None:
                if current_timestamp.tzinfo is None:
                    current_timestamp = current_timestamp.replace(
                        tzinfo=timezone.utc
                    )

                if position.timestamp <= current_timestamp:
                    return False

        await collection.update_one(
            {
                "mmsi": position.mmsi,
            },
            {
                "$set": position.model_dump(),
            },
            upsert=True,
        )

        return True

    async def get_current_vessels(self, limit: int = 100):
        cursor = (
            database["vessels"]
            .find({}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )

        return [vessel async for vessel in cursor]

    async def get_current_vessel_by_mmsi(self, mmsi: str):
        return await database["vessels"].find_one(
            {"mmsi": mmsi},
            {"_id": 0},
        )

    async def get_vessel_position_history(
        self,
        mmsi: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ):
        query = {"mmsi": mmsi}

        if start or end:
            query["timestamp"] = {}

            if start:
                query["timestamp"]["$gte"] = start

            if end:
                query["timestamp"]["$lte"] = end

        cursor = (
            database["vessel_positions"]
            .find(query, {"_id": 0})
            .sort("timestamp", 1)
            .limit(limit)
        )

        return [position async for position in cursor]