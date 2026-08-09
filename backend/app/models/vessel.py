from datetime import datetime

from pydantic import BaseModel


class VesselPosition(BaseModel):
    mmsi: str
    imo: str | None = None

    vessel_name: str | None = None

    latitude: float
    longitude: float

    sog: float | None = None
    cog: float | None = None
    heading: float | None = None

    nav_status: int | None = None

    timestamp: datetime

    source: str = "VesselAPI"