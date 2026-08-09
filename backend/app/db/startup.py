from app.db.database import database


async def create_indexes():

    # Existing Ship collection
    await database["ships"].create_index(
        "mmsi",
        unique=True
    )

    # Historical vessel positions
    await database["vessel_positions"].create_index(
        [
            ("mmsi", 1),
            ("timestamp", 1)
        ],
        unique=True
    )

    # Useful for time-based queries
    await database["vessel_positions"].create_index(
        "timestamp"
    )
    
        # Current vessel state
    await database["vessels"].create_index(
        "mmsi",
        unique=True
    )