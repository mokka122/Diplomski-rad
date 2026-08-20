import asyncio

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from app.repositories.redis_traffic_repository import (
    RedisTrafficRepository,
)

from app.services.hourly_traffic_snapshot_service import (
    hourly_traffic_snapshot_service,
)

from app.services.traffic_event_service import (
    TrafficEvent,
    TrafficEventType,
)


async def main():
    print("=" * 90)
    print(
        "OCEANEYE - HOURLY TRAFFIC SNAPSHOT TEST"
    )
    print("=" * 90)

    redis_repository = (
        RedisTrafficRepository()
    )

    # ==================================================================================
    # USE A SAFE TEST HOUR
    # ==================================================================================

    test_hour = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            days=2
        )
    ).replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    # Remove possible previous test data.
    await redis_repository.delete_hour(
        test_hour
    )

    # ==================================================================================
    # TEST 1
    # HOUR SHOULD NOT EXIST
    # ==================================================================================

    exists_before = (
        await redis_repository
        .hour_exists(
            test_hour
        )
    )

    print()
    print(
        f"1. Exists before snapshot: "
        f"{exists_before}"
    )

    assert exists_before is False

    print(
        "   Missing hour detection: PASS"
    )

    # ==================================================================================
    # TEST 2
    # INITIALIZE ZERO SNAPSHOT
    # ==================================================================================

    created = (
        await hourly_traffic_snapshot_service
        .ensure_current_hour(
            test_hour
        )
    )

    print()
    print(
        f"2. Snapshot created: "
        f"{created}"
    )

    assert created is True

    exists_after = (
        await redis_repository
        .hour_exists(
            test_hour
        )
    )

    assert exists_after is True

    print(
        "   Snapshot initialization: PASS"
    )

    # ==================================================================================
    # TEST 3
    # ALL COUNTERS SHOULD BE ZERO
    # ==================================================================================

    traffic = (
        await redis_repository
        .get_hour(
            test_hour
        )
    )

    print()
    print(
        "3. Initial hourly traffic:"
    )

    print(
        traffic
    )

    expected_zero_fields = [
        "total_events",
        "arrivals",
        "departures",
        "unique_vessels",

        "passenger_events",
        "cargo_events",
        "fishing_events",
        "tanker_events",
        "auxiliary_events",
        "tug_events",
    ]

    for field in expected_zero_fields:

        assert (
            traffic[field]
            == 0
        )

    print(
        "   Known zero counters: PASS"
    )

    # ==================================================================================
    # TEST 4
    # CALLING ENSURE AGAIN MUST NOT RESET ANYTHING
    # ==================================================================================

    created_again = (
        await hourly_traffic_snapshot_service
        .ensure_current_hour(
            test_hour
        )
    )

    assert created_again is False

    print()
    print(
        "4. Existing snapshot preserved: PASS"
    )

    # ==================================================================================
    # TEST 5
    # ADD REAL EVENT
    # ==================================================================================

    event_time = (
        test_hour
        + timedelta(
            minutes=20
        )
    )

    event = TrafficEvent(
        mmsi="257888888",

        event_type=(
            TrafficEventType.ENTRY
        ),

        timestamp=event_time,

        latitude=62.47,
        longitude=6.14,

        vessel_name=(
            "OceanEye Snapshot Test"
        ),

        ship_type=70,

        sog=7.5,
    )

    await redis_repository.register_event(
        event
    )

    traffic_after_event = (
        await redis_repository
        .get_hour(
            test_hour
        )
    )

    print()
    print(
        "5. Traffic after cargo ENTRY:"
    )

    print(
        traffic_after_event
    )

    assert (
        traffic_after_event[
            "total_events"
        ]
        == 1
    )

    assert (
        traffic_after_event[
            "arrivals"
        ]
        == 1
    )

    assert (
        traffic_after_event[
            "departures"
        ]
        == 0
    )

    assert (
        traffic_after_event[
            "unique_vessels"
        ]
        == 1
    )

    assert (
        traffic_after_event[
            "cargo_events"
        ]
        == 1
    )

    print(
        "   Event counters: PASS"
    )

    # ==================================================================================
    # TEST 6
    # ENSURE MUST NOT RESET EXISTING REAL DATA
    # ==================================================================================

    await (
        hourly_traffic_snapshot_service
        .ensure_current_hour(
            test_hour
        )
    )

    final_traffic = (
        await redis_repository
        .get_hour(
            test_hour
        )
    )

    assert (
        final_traffic[
            "total_events"
        ]
        == 1
    )

    assert (
        final_traffic[
            "arrivals"
        ]
        == 1
    )

    assert (
        final_traffic[
            "cargo_events"
        ]
        == 1
    )

    print()
    print(
        "6. Snapshot does not overwrite "
        "real data: PASS"
    )

    # ==================================================================================
    # STATUS
    # ==================================================================================

    print()
    print(
        "Snapshot service status:"
    )

    print(
        hourly_traffic_snapshot_service
        .get_status()
    )

    # ==================================================================================
    # CLEAN TEST DATA
    # ==================================================================================

    await redis_repository.delete_hour(
        test_hour
    )

    print()
    print(
        "Test Redis hour removed."
    )

    print()
    print("=" * 90)
    print(
        "ALL HOURLY SNAPSHOT TESTS PASSED"
    )
    print("=" * 90)


if __name__ == "__main__":

    asyncio.run(
        main()
    )