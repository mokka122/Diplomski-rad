from datetime import datetime

from app.db.database import database
from app.services.traffic_event_service import TrafficEvent


class TrafficEventRepository:
    COLLECTION_NAME = "traffic_events"

    @property
    def collection(self):
        return database[self.COLLECTION_NAME]

    async def save_event(
        self,
        event: TrafficEvent,
    ) -> bool:
        """
        Persist a detected ENTRY / EXIT event.

        Upsert is used so that the same event cannot be inserted
        multiple times if a Kafka message is processed again.

        Returns:
            True  -> a new event was inserted
            False -> the event already existed
        """

        document = event.to_dict()

        result = await self.collection.update_one(
            {
                "mmsi": event.mmsi,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp,
            },
            {
                "$setOnInsert": document,
            },
            upsert=True,
        )

        return result.upserted_id is not None

    async def get_events(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        event_type: str | None = None,
        limit: int = 500,
    ) -> list[dict]:

        query: dict = {}

        if start is not None or end is not None:
            query["timestamp"] = {}

            if start is not None:
                query["timestamp"]["$gte"] = start

            if end is not None:
                query["timestamp"]["$lte"] = end

        if event_type is not None:
            query["event_type"] = event_type

        cursor = (
            self.collection
            .find(
                query,
                {"_id": 0},
            )
            .sort("timestamp", -1)
            .limit(limit)
        )

        return [
            event
            async for event in cursor
        ]

    async def count_events(
        self,
    ) -> int:
        return await self.collection.count_documents(
            {}
        )