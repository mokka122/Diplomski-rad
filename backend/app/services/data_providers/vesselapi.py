import os

import httpx

from app.services.data_providers.base import DataProvider


class VesselAPIProvider(DataProvider):

    BASE_URL = "https://api.vesselapi.com/v1"

    def __init__(self):
        self.api_key = os.getenv("VESSELAPI_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "VESSELAPI_API_KEY is not configured."
            )

    async def get_vessels_in_area(
        self,
        lon_left: float,
        lon_right: float,
        lat_bottom: float,
        lat_top: float,
    ):
        url = f"{self.BASE_URL}/location/vessels/bounding-box"

        params = {
            "filter.lonLeft": lon_left,
            "filter.lonRight": lon_right,
            "filter.latBottom": lat_bottom,
            "filter.latTop": lat_top,
            "pagination.limit": 50,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params=params,
                headers=headers,
            )

        response.raise_for_status()

        return response.json()