from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TrafficCurrentResponse(BaseModel):
    timestamp_utc: datetime

    total_events: int
    arrivals: int
    departures: int
    unique_vessels: int
    
    passenger_events: int
    cargo_events: int
    fishing_events: int
    tanker_events: int
    auxiliary_events: int
    tug_events: int


class TrafficEventResponse(BaseModel):
    mmsi: str

    event_type: str

    timestamp: datetime

    latitude: float
    longitude: float

    vessel_name: Optional[str] = None
    ship_type: Optional[int] = None
    sog: Optional[float] = None

    source: str


class TrafficEventsResponse(BaseModel):
    count: int

    events: list[
        TrafficEventResponse
    ]


class TrafficGeofenceResponse(BaseModel):
    name: str
    type: str

    min_latitude: float
    max_latitude: float

    min_longitude: float
    max_longitude: float


class TrafficStatusResponse(BaseModel):
    tracked_vessels: int
    vessels_inside: int

    entries_detected: int
    exits_detected: int

    current_hour_total_events: int
    current_hour_arrivals: int
    current_hour_departures: int
    current_hour_unique_vessels: int