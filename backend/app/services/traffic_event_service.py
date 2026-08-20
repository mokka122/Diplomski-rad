from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from app.services.alesund_geofence import (
    is_inside_alesund,
)


# ======================================================================================
# EVENT TYPES
# ======================================================================================


class TrafficEventType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


# ======================================================================================
# RESULT MODEL
# ======================================================================================


@dataclass
class TrafficEvent:
    mmsi: str

    event_type: TrafficEventType

    timestamp: datetime

    latitude: float
    longitude: float

    vessel_name: Optional[str] = None

    ship_type: Optional[int] = None

    sog: Optional[float] = None

    source: str = "BarentsWatch"

    def to_dict(self) -> dict:
        return {
            "mmsi": self.mmsi,

            "event_type":
                self.event_type.value,

            "timestamp":
                self.timestamp,

            "latitude":
                self.latitude,

            "longitude":
                self.longitude,

            "vessel_name":
                self.vessel_name,

            "ship_type":
                self.ship_type,

            "sog":
                self.sog,

            "source":
                self.source,
        }


# ======================================================================================
# INTERNAL VESSEL STATE
# ======================================================================================


@dataclass
class VesselGeofenceState:
    inside: bool

    last_timestamp: datetime

    latitude: float
    longitude: float


# ======================================================================================
# SERVICE
# ======================================================================================


class TrafficEventService:
    """
    Detects vessel transitions across the configured Ålesund geofence.

    Example:

        outside -> inside = ENTRY
        inside  -> outside = EXIT

    The first observed AIS message for a vessel only establishes
    state and does NOT create an event.
    """

    def __init__(self) -> None:
        self._states: Dict[
            str,
            VesselGeofenceState,
        ] = {}

        self._entry_count = 0
        self._exit_count = 0

    # ==================================================================================
    # POSITION PROCESSING
    # ==================================================================================

    def process_position(
        self,
        vessel: dict,
    ) -> Optional[TrafficEvent]:

        mmsi = vessel.get(
            "mmsi"
        )

        latitude = vessel.get(
            "latitude"
        )

        longitude = vessel.get(
            "longitude"
        )

        if (
            mmsi is None
            or latitude is None
            or longitude is None
        ):
            return None

        mmsi = str(
            mmsi
        )

        try:
            latitude = float(
                latitude
            )

            longitude = float(
                longitude
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        timestamp = vessel.get(
            "timestamp"
        )

        if not isinstance(
            timestamp,
            datetime,
        ):
            timestamp = (
                datetime.now(
                    timezone.utc
                )
            )

        elif timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )

        current_inside = (
            is_inside_alesund(
                latitude=latitude,
                longitude=longitude,
            )
        )

        previous_state = (
            self._states.get(
                mmsi
            )
        )

        # ----------------------------------------------------------------------------------
        # First observation:
        #
        # establish vessel state only.
        #
        # We cannot know whether a vessel actually crossed the boundary before OceanEye
        # started observing it.
        # ----------------------------------------------------------------------------------

        if previous_state is None:

            self._states[
                mmsi
            ] = VesselGeofenceState(
                inside=current_inside,
                last_timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
            )

            return None

        # ----------------------------------------------------------------------------------
        # Ignore stale/out-of-order positions
        # ----------------------------------------------------------------------------------

        if (
            timestamp
            <
            previous_state.last_timestamp
        ):
            return None

        event = None

        # ----------------------------------------------------------------------------------
        # OUTSIDE -> INSIDE
        # ----------------------------------------------------------------------------------

        if (
            not previous_state.inside
            and current_inside
        ):

            event = TrafficEvent(
                mmsi=mmsi,
                event_type=(
                    TrafficEventType.ENTRY
                ),
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                vessel_name=vessel.get(
                    "vessel_name"
                ),
                ship_type=vessel.get(
                    "ship_type"
                ),
                sog=vessel.get(
                    "sog"
                ),
            )

            self._entry_count += 1

        # ----------------------------------------------------------------------------------
        # INSIDE -> OUTSIDE
        # ----------------------------------------------------------------------------------

        elif (
            previous_state.inside
            and not current_inside
        ):

            event = TrafficEvent(
                mmsi=mmsi,
                event_type=(
                    TrafficEventType.EXIT
                ),
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                vessel_name=vessel.get(
                    "vessel_name"
                ),
                ship_type=vessel.get(
                    "ship_type"
                ),
                sog=vessel.get(
                    "sog"
                ),
            )

            self._exit_count += 1

        # ----------------------------------------------------------------------------------
        # Update current state
        # ----------------------------------------------------------------------------------

        self._states[
            mmsi
        ] = VesselGeofenceState(
            inside=current_inside,
            last_timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
        )

        return event

    # ==================================================================================
    # STATUS
    # ==================================================================================

    def get_status(self) -> dict:

        vessels_inside = sum(
            1
            for state
            in self._states.values()
            if state.inside
        )

        return {
            "tracked_vessels":
                len(
                    self._states
                ),

            "vessels_inside":
                vessels_inside,

            "entries_detected":
                self._entry_count,

            "exits_detected":
                self._exit_count,
        }

    # ==================================================================================
    # TEST / RESET SUPPORT
    # ==================================================================================

    def reset(self) -> None:
        self._states.clear()

        self._entry_count = 0
        self._exit_count = 0


traffic_event_service = (
    TrafficEventService()
)