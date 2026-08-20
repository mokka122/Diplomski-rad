from datetime import (
    datetime,
    timedelta,
    timezone,
)

from app.services.traffic_event_service import (
    traffic_event_service,
)


def main() -> None:
    print("=" * 80)
    print("OCEANEYE - TRAFFIC EVENT TEST")
    print("=" * 80)

    traffic_event_service.reset()

    now = datetime.now(
        timezone.utc
    )

    # ----------------------------------------------------------------------------------
    # 1. First observation OUTSIDE
    #
    # Should establish state but produce NO event.
    # ----------------------------------------------------------------------------------

    vessel_outside = {
        "mmsi": "257123456",
        "vessel_name": "TEST VESSEL",
        "latitude": 62.40,
        "longitude": 6.14,
        "ship_type": 70,
        "sog": 8.5,
        "timestamp": now,
    }

    event = (
        traffic_event_service
        .process_position(
            vessel_outside
        )
    )

    print()
    print(
        "Initial outside position:",
        event,
    )

    assert event is None

    # ----------------------------------------------------------------------------------
    # 2. Vessel moves INSIDE
    #
    # Should generate ENTRY.
    # ----------------------------------------------------------------------------------

    vessel_inside = {
        **vessel_outside,

        "latitude": 62.47,
        "longitude": 6.14,

        "timestamp":
            now
            + timedelta(
                minutes=5
            ),
    }

    event = (
        traffic_event_service
        .process_position(
            vessel_inside
        )
    )

    print()
    print(
        "Outside -> inside:"
    )

    print(
        event.to_dict()
        if event
        else None
    )

    assert event is not None
    assert event.event_type.value == "ENTRY"

    # ----------------------------------------------------------------------------------
    # 3. Another INSIDE observation
    #
    # No duplicate ENTRY should be produced.
    # ----------------------------------------------------------------------------------

    vessel_still_inside = {
        **vessel_inside,

        "latitude": 62.48,
        "longitude": 6.16,

        "timestamp":
            now
            + timedelta(
                minutes=10
            ),
    }

    event = (
        traffic_event_service
        .process_position(
            vessel_still_inside
        )
    )

    print()
    print(
        "Inside -> inside:",
        event,
    )

    assert event is None

    # ----------------------------------------------------------------------------------
    # 4. Vessel leaves the area
    #
    # Should generate EXIT.
    # ----------------------------------------------------------------------------------

    vessel_exit = {
        **vessel_still_inside,

        "latitude": 62.40,
        "longitude": 6.14,

        "timestamp":
            now
            + timedelta(
                minutes=20
            ),
    }

    event = (
        traffic_event_service
        .process_position(
            vessel_exit
        )
    )

    print()
    print(
        "Inside -> outside:"
    )

    print(
        event.to_dict()
        if event
        else None
    )

    assert event is not None
    assert event.event_type.value == "EXIT"

    # ----------------------------------------------------------------------------------
    # STATUS
    # ----------------------------------------------------------------------------------

    print()
    print(
        "Status:"
    )

    print(
        traffic_event_service
        .get_status()
    )

    print()
    print("=" * 80)
    print("ALL TRAFFIC EVENT TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()