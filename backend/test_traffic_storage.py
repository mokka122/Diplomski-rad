import asyncio
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from app.repositories.redis_traffic_repository import (
    RedisTrafficRepository,
)

from app.repositories.traffic_event_repository import (
    TrafficEventRepository,
)

from app.services.traffic_event_service import (
    traffic_event_service,
)


async def main():
    print("=" * 90)
    print("OCEANEYE - TRAFFIC STORAGE INTEGRATION TEST")
    print("=" * 90)

    event_repository = (
        TrafficEventRepository()
    )

    redis_repository = (
        RedisTrafficRepository()
    )

    traffic_event_service.reset()

    now = (
        datetime.now(
            timezone.utc
        )
        .replace(
            minute=10,
            second=0,
            microsecond=0,
        )
    )

    # ==================================================================================
    # CLEAN CURRENT TEST HOUR IN REDIS
    # ==================================================================================

    await redis_repository.delete_hour(
        now
    )

    # ==================================================================================
    # FIRST POSITION — OUTSIDE
    # ==================================================================================

    outside = {
        "mmsi": "257999999",
        "vessel_name": "OceanEye Integration Test",
        "latitude": 62.40,
        "longitude": 6.14,
        "ship_type": 70,
        "sog": 8.0,
        "timestamp": now,
    }

    event = (
        traffic_event_service
        .process_position(
            outside
        )
    )

    assert event is None

    print()
    print(
        "1. Initial outside state: PASS"
    )

    # ==================================================================================
    # ENTRY
    # ==================================================================================

    inside = {
        **outside,

        "latitude": 62.47,
        "longitude": 6.14,

        "timestamp":
            now
            + timedelta(
                minutes=5
            ),
    }

    entry = (
        traffic_event_service
        .process_position(
            inside
        )
    )

    assert entry is not None
    assert entry.event_type.value == "ENTRY"

    inserted = (
        await event_repository
        .save_event(
            entry
        )
    )

    if inserted:
        await redis_repository.register_event(
            entry
        )

    print(
        "2. ENTRY detected: PASS"
    )

    print(
        f"   Mongo inserted: {inserted}"
    )

    # ==================================================================================
    # EXIT
    # ==================================================================================

    outside_again = {
        **inside,

        "latitude": 62.40,
        "longitude": 6.14,

        "timestamp":
            now
            + timedelta(
                minutes=20
            ),
    }

    exit_event = (
        traffic_event_service
        .process_position(
            outside_again
        )
    )

    assert exit_event is not None
    assert (
        exit_event.event_type.value
        == "EXIT"
    )

    inserted_exit = (
        await event_repository
        .save_event(
            exit_event
        )
    )

    if inserted_exit:
        await redis_repository.register_event(
            exit_event
        )

    print(
        "3. EXIT detected: PASS"
    )

    print(
        f"   Mongo inserted: "
        f"{inserted_exit}"
    )

    # ==================================================================================
    # REDIS RESULT
    # ==================================================================================

    traffic = (
        await redis_repository
        .get_hour(
            now
        )
    )

    print()
    print("Redis hourly traffic:")
    print(traffic)

    assert (
        traffic["total_events"]
        == 2
    )

    assert (
        traffic["arrivals"]
        == 1
    )

    assert (
        traffic["departures"]
        == 1
    )

    assert (
        traffic["unique_vessels"]
        == 1
    )

    print()
    print(
        "4. Redis counters: PASS"
    )

    # ==================================================================================
    # MONGODB RESULT
    # ==================================================================================

    events = (
        await event_repository
        .get_events(
            start=now,
            end=(
                now
                + timedelta(
                    hours=1
                )
            ),
            limit=20,
        )
    )

    matching_events = [
        event
        for event in events
        if event.get("mmsi")
        == "257999999"
    ]

    print()
    print(
        "MongoDB traffic events:"
    )

    for stored_event in matching_events:
        print(
            stored_event
        )

    assert (
        len(
            matching_events
        )
        >= 2
    )

    print()
    print(
        "5. MongoDB persistence: PASS"
    )

    print()
    print("=" * 90)
    print(
        "ALL TRAFFIC STORAGE TESTS PASSED"
    )
    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(
        main()
    )