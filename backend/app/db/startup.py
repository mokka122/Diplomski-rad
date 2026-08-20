from app.db.database import database


async def create_indexes():
    # ==================================================================================
    # CURRENT VESSEL STATE
    # ==================================================================================

    await database["vessels"].create_index(
        "mmsi",
        unique=True,
    )

    # ==================================================================================
    # AIS POSITION HISTORY
    # ==================================================================================

    await database["vessel_positions"].create_index(
        [
            ("mmsi", 1),
            ("timestamp", 1),
        ],
        unique=True,
    )

    await database["vessel_positions"].create_index(
        "timestamp"
    )

    # ==================================================================================
    # ÅLESUND TRAFFIC EVENTS
    # ==================================================================================

    await database["traffic_events"].create_index(
        [
            ("mmsi", 1),
            ("event_type", 1),
            ("timestamp", 1),
        ],
        unique=True,
    )

    await database["traffic_events"].create_index(
        "timestamp"
    )

    await database["traffic_events"].create_index(
        [
            ("event_type", 1),
            ("timestamp", -1),
        ]
    )