import json
import os
from collections.abc import AsyncIterator

import httpx
from dotenv import load_dotenv

from app.services.data_providers.base import DataProvider


load_dotenv()


class BarentsWatchProvider(DataProvider):
    TOKEN_URL = "https://id.barentswatch.no/connect/token"
    AIS_STREAM_URL = "https://live.ais.barentswatch.no/v1/combined"

    def __init__(self):
        self.client_id = os.getenv("BARENTSWATCH_CLIENT_ID")
        self.client_secret = os.getenv("BARENTSWATCH_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "BARENTSWATCH_CLIENT_ID or "
                "BARENTSWATCH_CLIENT_SECRET is missing from .env"
            )

    async def get_access_token(self) -> str:
        data = {
            "grant_type": "client_credentials",
            "scope": "ais",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.TOKEN_URL,
                data=data,
                auth=(self.client_id, self.client_secret),
            )

        response.raise_for_status()

        return response.json()["access_token"]

    async def stream_messages(self) -> AsyncIterator[dict]:
        token = await self.get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=None,
            headers=headers,
        ) as client:
            async with client.stream(
                "GET",
                self.AIS_STREAM_URL,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if isinstance(message, dict):
                        yield message