from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class Ship(BaseModel):

    mmsi: str

    ship_name: Optional[str] = None

    ship_type: Optional[str] = None

    status: Optional[str] = None

    latitude: float

    longitude: float

    speed: Optional[float] = None

    course: Optional[float] = None

    destination: Optional[str] = None

    timestamp: datetime