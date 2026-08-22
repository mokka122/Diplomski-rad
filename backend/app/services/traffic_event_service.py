from dataclasses import (
    dataclass,
)

from datetime import (
    datetime,
    timezone,
)

from enum import (
    Enum,
)

from typing import (
    Dict,
    Optional,
)


from app.repositories.redis_geofence_state_repository import (
    RedisGeofenceStateRepository,
)

from app.services.alesund_geofence import (
    is_inside_alesund,
)


# ======================================================================================
# EVENT TYPES
# ======================================================================================


class TrafficEventType(
    str,
    Enum,
):
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

    def to_dict(
        self,
    ) -> dict:

        return {
            "mmsi":
                self.mmsi,

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
    Detect vessel transitions across the OceanEye Ålesund
    operational study-area geofence.

    Transition semantics:

        outside -> inside = ENTRY
        inside  -> outside = EXIT

    State is cached in Python memory for speed and persisted
    in Redis so normal application restarts do not destroy
    boundary-transition context.

    If no previous state exists in either memory or Redis,
    the first observation establishes state only and does not
    generate an event.
    """

    def __init__(
        self,
    ) -> None:

        self._states: Dict[
            str,
            VesselGeofenceState,
        ] = {}

        self.redis_repository = (
            RedisGeofenceStateRepository()
        )

        # These diagnostic counters describe events detected
        # during the current FastAPI process lifetime.
        #
        # Persistent hourly counts remain stored separately
        # in RedisTrafficRepository.
        self._entry_count = 0
        self._exit_count = 0

    # ==================================================================================
    # LOAD PREVIOUS STATE
    # ==================================================================================

    async def _get_previous_state(
        self,
        mmsi: str,
    ) -> VesselGeofenceState | None:

        # ----------------------------------------------------------------------------------
        # Fast in-memory path
        # ----------------------------------------------------------------------------------

        memory_state = (
            self._states.get(
                mmsi
            )
        )

        if memory_state is not None:
            return memory_state

        # ----------------------------------------------------------------------------------
        # Restart recovery path
        # ----------------------------------------------------------------------------------

        redis_state = (
            await self
            .redis_repository
            .get_state(
                mmsi
            )
        )

        if redis_state is None:
            return None

        restored_state = (
            VesselGeofenceState(
                inside=(
                    redis_state[
                        "inside"
                    ]
                ),

                last_timestamp=(
                    redis_state[
                        "last_timestamp"
                    ]
                ),

                latitude=(
                    redis_state[
                        "latitude"
                    ]
                ),

                longitude=(
                    redis_state[
                        "longitude"
                    ]
                ),
            )
        )

        # Cache restored state locally.
        self._states[
            mmsi
        ] = restored_state

        return restored_state

    # ==================================================================================
    # SAVE CURRENT STATE
    # ==================================================================================

    async def _save_state(
        self,
        mmsi: str,
        state: VesselGeofenceState,
    ) -> None:

        # Local cache
        self._states[
            mmsi
        ] = state

        # Persistent Redis state
        await (
            self.redis_repository
            .save_state(
                mmsi=mmsi,
                inside=state.inside,
                last_timestamp=(
                    state.last_timestamp
                ),
                latitude=(
                    state.latitude
                ),
                longitude=(
                    state.longitude
                ),
            )
        )

    # ==================================================================================
    # POSITION PROCESSING
    # ==================================================================================

    async def process_position(
        self,
        vessel: dict,
    ) -> Optional[
        TrafficEvent
    ]:

        # ----------------------------------------------------------------------------------
        # Required vessel fields
        # ----------------------------------------------------------------------------------

        mmsi = (
            vessel.get(
                "mmsi"
            )
        )

        latitude = (
            vessel.get(
                "latitude"
            )
        )

        longitude = (
            vessel.get(
                "longitude"
            )
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

        # ----------------------------------------------------------------------------------
        # Timestamp
        # ----------------------------------------------------------------------------------

        timestamp = (
            vessel.get(
                "timestamp"
            )
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

            timestamp = (
                timestamp.replace(
                    tzinfo=timezone.utc
                )
            )

        else:

            timestamp = (
                timestamp.astimezone(
                    timezone.utc
                )
            )

        # ----------------------------------------------------------------------------------
        # Current geofence state
        # ----------------------------------------------------------------------------------

        current_inside = (
            is_inside_alesund(
                latitude=latitude,
                longitude=longitude,
            )
        )

        previous_state = (
            await self
            ._get_previous_state(
                mmsi
            )
        )

        # ----------------------------------------------------------------------------------
        # FIRST OBSERVATION
        # ----------------------------------------------------------------------------------
        #
        # No known previous state exists.
        #
        # We cannot infer a real crossing simply from seeing
        # the vessel for the first time.
        # ----------------------------------------------------------------------------------

        if previous_state is None:

            await self._save_state(
                mmsi=mmsi,

                state=(
                    VesselGeofenceState(
                        inside=current_inside,
                        last_timestamp=timestamp,
                        latitude=latitude,
                        longitude=longitude,
                    )
                ),
            )

            return None

        # ----------------------------------------------------------------------------------
        # IGNORE STALE / OUT-OF-ORDER AIS
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

            event = (
                TrafficEvent(
                    mmsi=mmsi,

                    event_type=(
                        TrafficEventType.ENTRY
                    ),

                    timestamp=timestamp,

                    latitude=latitude,
                    longitude=longitude,

                    vessel_name=(
                        vessel.get(
                            "vessel_name"
                        )
                    ),

                    ship_type=(
                        vessel.get(
                            "ship_type"
                        )
                    ),

                    sog=(
                        vessel.get(
                            "sog"
                        )
                    ),
                )
            )

            self._entry_count += 1

        # ----------------------------------------------------------------------------------
        # INSIDE -> OUTSIDE
        # ----------------------------------------------------------------------------------

        elif (
            previous_state.inside
            and not current_inside
        ):

            event = (
                TrafficEvent(
                    mmsi=mmsi,

                    event_type=(
                        TrafficEventType.EXIT
                    ),

                    timestamp=timestamp,

                    latitude=latitude,
                    longitude=longitude,

                    vessel_name=(
                        vessel.get(
                            "vessel_name"
                        )
                    ),

                    ship_type=(
                        vessel.get(
                            "ship_type"
                        )
                    ),

                    sog=(
                        vessel.get(
                            "sog"
                        )
                    ),
                )
            )

            self._exit_count += 1

        # ----------------------------------------------------------------------------------
        # SAVE LATEST STATE
        # ----------------------------------------------------------------------------------

        await self._save_state(
            mmsi=mmsi,

            state=(
                VesselGeofenceState(
                    inside=current_inside,
                    last_timestamp=timestamp,
                    latitude=latitude,
                    longitude=longitude,
                )
            ),
        )

        return event

    # ==================================================================================
    # STATUS
    # ==================================================================================

    def get_status(
        self,
    ) -> dict:

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
    # TEST / MEMORY RESET
    # ==================================================================================

    def reset(
        self,
    ) -> None:
        """
        Reset only the current-process diagnostic state.

        Redis-backed vessel geofence states are intentionally
        not deleted by this helper.
        """

        self._states.clear()

        self._entry_count = 0
        self._exit_count = 0


traffic_event_service = (
    TrafficEventService()
)