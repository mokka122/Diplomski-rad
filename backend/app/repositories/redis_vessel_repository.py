import json

from app.db.redis import redis_client


class RedisVesselRepository:

    KEY_PREFIX = "vessel:"

    def _get_key(self, mmsi: str) -> str:
        return f"{self.KEY_PREFIX}{mmsi}"

    async def save_current_vessel(self, vessel):
        key = self._get_key(vessel.mmsi)

        await redis_client.set(
            key,
            json.dumps(
                vessel.model_dump(mode="json")
            ),
        )

    async def get_current_vessel(self, mmsi: str):
        key = self._get_key(mmsi)

        data = await redis_client.get(key)

        if data is None:
            return None

        return json.loads(data)

    async def delete_current_vessel(self, mmsi: str):
        key = self._get_key(mmsi)

        await redis_client.delete(key)