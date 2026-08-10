from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.models.vessel import VesselPosition
from app.repositories.vessel_repository import VesselRepository


router = APIRouter(
    prefix="/testing",
    tags=["Testing"],
)


@router.post("/save-vessel")
async def save_test_vessel():
    position = VesselPosition(
        mmsi="TEST123456",
        vessel_name="Test Vessel",
        latitude=61.300407,
        longitude=5.10939,
        sog=8.5,
        cog=120.0,
        heading=118.0,
        nav_status=0,
        ship_type=70,
        rate_of_turn=0.0,
        timestamp=datetime.now(timezone.utc),
        source="Test",
    )

    repository = VesselRepository()

    position_saved = await repository.save_position(position)
    current_updated = await repository.upsert_current_vessel(position)

    return {
        "message": "Test vessel processed",
        "position_saved": position_saved,
        "current_state_updated": current_updated,
        "mmsi": position.mmsi,
    }


@router.post("/save-history")
async def save_test_history():
    repository = VesselRepository()
    base_time = datetime.now(timezone.utc)

    positions = [
        VesselPosition(
            mmsi="TESTHISTORY123",
            vessel_name="History Test Vessel",
            latitude=61.300407,
            longitude=5.10939,
            sog=6.5,
            cog=100.0,
            heading=98.0,
            nav_status=0,
            ship_type=70,
            rate_of_turn=0.0,
            timestamp=base_time,
            source="Test",
        ),
        VesselPosition(
            mmsi="TESTHISTORY123",
            vessel_name="History Test Vessel",
            latitude=61.305000,
            longitude=5.115000,
            sog=8.0,
            cog=105.0,
            heading=103.0,
            nav_status=0,
            ship_type=70,
            rate_of_turn=0.0,
            timestamp=base_time + timedelta(minutes=5),
            source="Test",
        ),
    ]

    for position in positions:
        await repository.save_position(position)
        await repository.upsert_current_vessel(position)

    return {
        "message": "Historical test data saved",
        "mmsi": "TESTHISTORY123",
        "positions_saved": len(positions),
    }