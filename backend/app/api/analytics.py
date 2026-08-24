from datetime import (
    datetime,
    timedelta,
    timezone,
)

from fastapi import (
    APIRouter,
    Query,
)

from app.repositories.redis_traffic_repository import (
    RedisTrafficRepository,
)

from app.services.traffic_event_service import (
    traffic_event_service,
)


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


redis_traffic_repository = (
    RedisTrafficRepository()
)


# ======================================================================================
# HELPERS
# ======================================================================================

def normalize_hour(
    timestamp: datetime,
) -> datetime:

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(
            tzinfo=timezone.utc
        )

    timestamp = timestamp.astimezone(
        timezone.utc
    )

    return timestamp.replace(
        minute=0,
        second=0,
        microsecond=0,
    )


def build_hour_range(
    hours: int,
    now: datetime,
) -> list[datetime]:

    current_hour = normalize_hour(
        now
    )

    return [
        current_hour
        - timedelta(
            hours=offset
        )
        for offset in reversed(
            range(hours)
        )
    ]


async def get_hour_with_availability(
    timestamp: datetime,
) -> dict:

    exists = (
        await redis_traffic_repository
        .hour_exists(
            timestamp
        )
    )

    data = (
        await redis_traffic_repository
        .get_hour(
            timestamp
        )
    )

    data["data_available"] = exists

    return data


async def get_hours_with_availability(
    timestamps: list[datetime],
) -> list[dict]:

    results = []

    for timestamp in timestamps:
        results.append(
            await get_hour_with_availability(
                timestamp
            )
        )

    return results


# ======================================================================================
# LIVE ANALYTICS
# ======================================================================================

@router.get("/live")
async def get_live_analytics(
    hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description=(
            "Number of recent UTC hours to include. "
            "Maximum is 168 hours / 7 days."
        ),
    ),
):
    """
    Return short-term live maritime traffic analytics
    for the OceanEye Ålesund operational study area.

    ENTRY and EXIT values are project-defined
    arrival-like / departure-like proxy events.

    Missing Redis hours are explicitly marked with
    data_available=false and must not be interpreted
    as confirmed zero traffic.
    """

    now = datetime.now(
        timezone.utc
    )

    timestamps = build_hour_range(
        hours=hours,
        now=now,
    )

    hourly_data = (
        await get_hours_with_availability(
            timestamps
        )
    )

    geofence_status = (
        traffic_event_service
        .get_status()
    )

    # ==================================================================================
    # OBSERVED DATA ONLY
    # ==================================================================================

    observed_hourly_data = [
        hour
        for hour in hourly_data
        if hour[
            "data_available"
        ]
    ]

    observed_hours = len(
        observed_hourly_data
    )

    missing_hours = (
        hours
        - observed_hours
    )

    coverage_percent = round(
        (
            observed_hours
            / hours
            * 100
        )
        if hours
        else 0,
        1,
    )

    # ==================================================================================
    # HOURLY SERIES
    # ==================================================================================

    hourly_traffic = []

    for hour in hourly_data:

        hourly_traffic.append(
            {
                "timestamp_utc":
                    hour[
                        "timestamp_utc"
                    ],

                "data_available":
                    hour[
                        "data_available"
                    ],

                "unique_vessels":
                    (
                        hour[
                            "unique_vessels"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),

                "total_events":
                    (
                        hour[
                            "total_events"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),

                "entries":
                    (
                        hour[
                            "arrivals"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),

                "exits":
                    (
                        hour[
                            "departures"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),

                "passenger_events":
                    (
                        hour[
                            "passenger_events"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),

                "cargo_events":
                    (
                        hour[
                            "cargo_events"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),

                "fishing_events":
                    (
                        hour[
                            "fishing_events"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),

                "tanker_events":
                    (
                        hour[
                            "tanker_events"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),

                "auxiliary_events":
                    (
                        hour[
                            "auxiliary_events"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),

                "tug_events":
                    (
                        hour[
                            "tug_events"
                        ]
                        if hour[
                            "data_available"
                        ]
                        else None
                    ),
            }
        )

    # ==================================================================================
    # REQUESTED-WINDOW TOTALS
    # ==================================================================================

    total_events = sum(
        hour[
            "total_events"
        ]
        for hour
        in observed_hourly_data
    )

    total_entries = sum(
        hour[
            "arrivals"
        ]
        for hour
        in observed_hourly_data
    )

    total_exits = sum(
        hour[
            "departures"
        ]
        for hour
        in observed_hourly_data
    )

    # ==================================================================================
    # TODAY
    # ==================================================================================

    today_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    today_hour_count = (
        now.hour
        + 1
    )

    today_timestamps = [
        today_start
        + timedelta(
            hours=hour_offset
        )
        for hour_offset in range(
            today_hour_count
        )
    ]

    today_data = (
        await get_hours_with_availability(
            today_timestamps
        )
    )

    observed_today_data = [
        hour
        for hour in today_data
        if hour[
            "data_available"
        ]
    ]

    entries_today = sum(
        hour[
            "arrivals"
        ]
        for hour
        in observed_today_data
    )

    exits_today = sum(
        hour[
            "departures"
        ]
        for hour
        in observed_today_data
    )

    events_today = sum(
        hour[
            "total_events"
        ]
        for hour
        in observed_today_data
    )

    today_observed_hours = len(
        observed_today_data
    )

    today_missing_hours = (
        today_hour_count
        - today_observed_hours
    )

    today_coverage_percent = round(
        (
            today_observed_hours
            / today_hour_count
            * 100
        )
        if today_hour_count
        else 0,
        1,
    )

    # ==================================================================================
    # VESSEL TYPE DISTRIBUTION
    # ==================================================================================

    vessel_type_distribution = {
        "passenger":
            sum(
                hour[
                    "passenger_events"
                ]
                for hour
                in observed_hourly_data
            ),

        "cargo":
            sum(
                hour[
                    "cargo_events"
                ]
                for hour
                in observed_hourly_data
            ),

        "fishing":
            sum(
                hour[
                    "fishing_events"
                ]
                for hour
                in observed_hourly_data
            ),

        "tanker":
            sum(
                hour[
                    "tanker_events"
                ]
                for hour
                in observed_hourly_data
            ),

        "auxiliary":
            sum(
                hour[
                    "auxiliary_events"
                ]
                for hour
                in observed_hourly_data
            ),

        "tug":
            sum(
                hour[
                    "tug_events"
                ]
                for hour
                in observed_hourly_data
            ),
    }

    # ==================================================================================
    # CURRENT HOUR
    # ==================================================================================

    current_hour = (
        hourly_data[-1]
        if hourly_data
        else await get_hour_with_availability(
            now
        )
    )

    # ==================================================================================
    # RESPONSE
    # ==================================================================================

    return {
        "study_area":
            "Ålesund OceanEye operational study area",

        "window_hours":
            hours,

        "coverage": {
            "requested_hours":
                hours,

            "observed_hours":
                observed_hours,

            "missing_hours":
                missing_hours,

            "coverage_percent":
                coverage_percent,
        },

        "today_coverage": {
            "requested_hours":
                today_hour_count,

            "observed_hours":
                today_observed_hours,

            "missing_hours":
                today_missing_hours,

            "coverage_percent":
                today_coverage_percent,
        },

        "summary": {
            "vessels_inside_area":
                geofence_status[
                    "vessels_inside"
                ],

            "tracked_geofence_vessels":
                geofence_status[
                    "tracked_vessels"
                ],

            "entries_today":
                entries_today,

            "exits_today":
                exits_today,

            "events_today":
                events_today,

            "window_total_events":
                total_events,

            "window_entries":
                total_entries,

            "window_exits":
                total_exits,
        },

        "current_hour": {
            "timestamp_utc":
                current_hour[
                    "timestamp_utc"
                ],

            "data_available":
                current_hour[
                    "data_available"
                ],

            "unique_vessels":
                (
                    current_hour[
                        "unique_vessels"
                    ]
                    if current_hour[
                        "data_available"
                    ]
                    else None
                ),

            "total_events":
                (
                    current_hour[
                        "total_events"
                    ]
                    if current_hour[
                        "data_available"
                    ]
                    else None
                ),

            "entries":
                (
                    current_hour[
                        "arrivals"
                    ]
                    if current_hour[
                        "data_available"
                    ]
                    else None
                ),

            "exits":
                (
                    current_hour[
                        "departures"
                    ]
                    if current_hour[
                        "data_available"
                    ]
                    else None
                ),
        },

        "vessel_type_distribution":
            vessel_type_distribution,

        "hourly_traffic":
            hourly_traffic,

        "updated_at":
            now.isoformat(),
    }