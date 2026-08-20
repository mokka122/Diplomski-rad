from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Query,
)

from app.models.traffic import (
    TrafficCurrentResponse,
    TrafficEventsResponse,
    TrafficGeofenceResponse,
    TrafficStatusResponse,
)

from app.repositories.redis_traffic_repository import (
    RedisTrafficRepository,
)

from app.repositories.traffic_event_repository import (
    TrafficEventRepository,
)

from app.services.alesund_geofence import (
    get_alesund_geofence,
)

from app.services.traffic_event_service import (
    traffic_event_service,
)

from app.services.live_feature_builder import (
    live_feature_builder,
)

from app.services.ais_ship_type_mapper import (
    get_ship_type_mapping_info,
)

from app.services.hourly_traffic_snapshot_service import (
    hourly_traffic_snapshot_service,
)


router = APIRouter(
    prefix="/traffic",
    tags=["Traffic"],
)


traffic_event_repository = (
    TrafficEventRepository()
)

redis_traffic_repository = (
    RedisTrafficRepository()
)


# ======================================================================================
# CURRENT TRAFFIC
# ======================================================================================

@router.get(
    "/current",
    response_model=TrafficCurrentResponse,
)
async def get_current_traffic():
    """
    Return live Ålesund traffic counters
    for the current UTC hour.
    """

    traffic = (
        await redis_traffic_repository
        .get_current_hour()
    )

    return traffic


# ======================================================================================
# STATUS
# ======================================================================================

@router.get(
    "/status",
    response_model=TrafficStatusResponse,
)
async def get_traffic_status():
    """
    Return status of the Ålesund geofence detector
    together with current-hour traffic counters.
    """

    geofence_status = (
        traffic_event_service
        .get_status()
    )

    current = (
        await redis_traffic_repository
        .get_current_hour()
    )

    return {
        "tracked_vessels":
            geofence_status[
                "tracked_vessels"
            ],

        "vessels_inside":
            geofence_status[
                "vessels_inside"
            ],

        "entries_detected":
            geofence_status[
                "entries_detected"
            ],

        "exits_detected":
            geofence_status[
                "exits_detected"
            ],

        "current_hour_total_events":
            current[
                "total_events"
            ],

        "current_hour_arrivals":
            current[
                "arrivals"
            ],

        "current_hour_departures":
            current[
                "departures"
            ],

        "current_hour_unique_vessels":
            current[
                "unique_vessels"
            ],
    }


# ======================================================================================
# EVENT HISTORY
# ======================================================================================

@router.get(
    "/events",
    response_model=TrafficEventsResponse,
)
async def get_traffic_events(
    start: datetime | None = Query(
        default=None,
        description=(
            "Start timestamp in ISO 8601 format"
        ),
    ),

    end: datetime | None = Query(
        default=None,
        description=(
            "End timestamp in ISO 8601 format"
        ),
    ),

    event_type: str | None = Query(
        default=None,
        pattern="^(ENTRY|EXIT)$",
        description=(
            "Optional event type: ENTRY or EXIT"
        ),
    ),

    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
):
    """
    Return detected Ålesund ENTRY / EXIT events
    stored in MongoDB.
    """

    events = (
        await traffic_event_repository
        .get_events(
            start=start,
            end=end,
            event_type=event_type,
            limit=limit,
        )
    )

    return {
        "count": len(
            events
        ),

        "events": events,
    }


# ======================================================================================
# GEOFENCE
# ======================================================================================

@router.get(
    "/geofence",
    response_model=TrafficGeofenceResponse,
)
async def get_traffic_geofence():
    """
    Return the currently configured Ålesund
    maritime study-area bounding box.
    """

    return get_alesund_geofence()

# ======================================================================================
# LIVE ML FEATURES
# ======================================================================================

@router.get(
    "/features/current",
)
async def get_current_ml_features():
    """
    Build the current 42-feature live ML input.

    This endpoint does NOT require a trained model.

    It allows the live BarentsWatch -> Redis -> ML feature
    pipeline to be inspected and tested independently.
    """

    return await (
        live_feature_builder
        .build_features()
    )


# ======================================================================================
# AIS SHIP TYPE MAPPING
# ======================================================================================

@router.get(
    "/ship-type-mapping",
)
async def get_ais_ship_type_mapping():
    """
    Return documentation of the AIS ship type
    -> OceanEye traffic group proxy mapping.
    """

    return get_ship_type_mapping_info()

# ======================================================================================
# HOURLY SNAPSHOT STATUS
# ======================================================================================

@router.get(
    "/snapshot/status",
)
async def get_hourly_snapshot_status():
    """
    Return status of the background hourly traffic
    snapshot service.

    The service ensures that hours with genuinely
    zero traffic are represented explicitly in Redis.
    """

    return (
        hourly_traffic_snapshot_service
        .get_status()
    )