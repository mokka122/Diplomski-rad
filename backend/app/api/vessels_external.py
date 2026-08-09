from fastapi import APIRouter

from app.services.data_providers.vesselapi import VesselAPIProvider
from app.services.normalizer import normalize_vessel

from datetime import datetime, timezone, timedelta

from app.repositories.vessel_repository import VesselRepository
from app.models.vessel import VesselPosition

router = APIRouter(
    prefix="/external",
    tags=["External Data"],
)


@router.get("/vessels")
async def get_external_vessels():

    provider = VesselAPIProvider()

    data = await provider.get_vessels_in_area(
        lon_left=14.25,
        lon_right=14.55,
        lat_bottom=45.20,
        lat_top=45.45,
    )

    return data


@router.get("/vessels/normalized")
async def get_normalized_vessels():

    provider = VesselAPIProvider()

    data = await provider.get_vessels_in_area(
        lon_left=14.25,
        lon_right=14.55,
        lat_bottom=45.20,
        lat_top=45.45,
    )

    vessels = data.get("vessels", [])

    normalized = [
        normalize_vessel(vessel)
        for vessel in vessels
    ]

    return {
        "count": len(normalized),
        "vessels": normalized,
    }
    
@router.post("/test-save")
async def test_save_vessel():

    position = VesselPosition(
        mmsi="TEST123456",
        imo="TESTIMO",
        vessel_name="Test Vessel",
        latitude=45.327,
        longitude=14.442,
        sog=8.5,
        cog=120.0,
        heading=118.0,
        nav_status=0,
        timestamp=datetime.now(timezone.utc),
        source="Test",
    )

    repository = VesselRepository()

    await repository.save_position(position)
    await repository.upsert_current_vessel(position)

    return {
        "message": "Test vessel saved successfully",
        "mmsi": position.mmsi,
    }
    
@router.post("/test-save-history")
async def test_save_history():

    repository = VesselRepository()

    base_time = datetime.now(timezone.utc)

    first_position = VesselPosition(
        mmsi="TESTHISTORY123",
        imo="TESTIMO123",
        vessel_name="History Test Vessel",
        latitude=45.320,
        longitude=14.430,
        sog=6.5,
        cog=100.0,
        heading=98.0,
        nav_status=0,
        timestamp=base_time,
        source="Test",
    )

    second_position = VesselPosition(
        mmsi="TESTHISTORY123",
        imo="TESTIMO123",
        vessel_name="History Test Vessel",
        latitude=45.325,
        longitude=14.435,
        sog=8.0,
        cog=105.0,
        heading=103.0,
        nav_status=0,
        timestamp=base_time + timedelta(minutes=5),
        source="Test",
    )

    await repository.save_position(first_position)
    await repository.upsert_current_vessel(first_position)

    await repository.save_position(second_position)
    await repository.upsert_current_vessel(second_position)

    return {
        "message": "Historical test data saved successfully",
        "mmsi": "TESTHISTORY123",
        "positions_saved": 2,
        "current_position": {
            "latitude": second_position.latitude,
            "longitude": second_position.longitude,
            "timestamp": second_position.timestamp,
        },
    }