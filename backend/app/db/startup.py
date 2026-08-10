from app.db.database import database


async def create_indexes():
    await database["vessels"].create_index(
        "mmsi",
        unique=True,
    )

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