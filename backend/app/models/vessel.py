from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


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
    ship_type: int | None = None
    rate_of_turn: float | None = None

    timestamp: datetime
    source: str = "BarentsWatch"

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")

        return value.astimezone(timezone.utc)