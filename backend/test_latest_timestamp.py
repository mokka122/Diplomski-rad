import asyncio

from app.db.database import database


async def main():
    latest_inserted_position = await database[
        "vessel_positions"
    ].find_one(
        {},
        sort=[("_id", -1)],
    )

    latest_timestamp_position = await database[
        "vessel_positions"
    ].find_one(
        {},
        sort=[("timestamp", -1)],
    )

    print("=" * 70)
    print("LATEST DOCUMENT BY INSERT ORDER")
    print("=" * 70)

    if latest_inserted_position:
        print(
            "Mongo inserted at:",
            latest_inserted_position["_id"].generation_time,
        )
        print(
            "AIS timestamp:",
            latest_inserted_position.get("timestamp"),
        )
        print(
            "MMSI:",
            latest_inserted_position.get("mmsi"),
        )
    else:
        print("No vessel_positions documents found.")

    print()

    print("=" * 70)
    print("LATEST DOCUMENT BY AIS TIMESTAMP")
    print("=" * 70)

    if latest_timestamp_position:
        print(
            "Mongo inserted at:",
            latest_timestamp_position["_id"].generation_time,
        )
        print(
            "AIS timestamp:",
            latest_timestamp_position.get("timestamp"),
        )
        print(
            "MMSI:",
            latest_timestamp_position.get("mmsi"),
        )
    else:
        print("No vessel_positions documents found.")


if __name__ == "__main__":
    asyncio.run(main())