from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.repositories.vessel_repository import VesselRepository


router = APIRouter(
    prefix="/vessels",
    tags=["Vessels"],
)


@router.get("/")
async def get_current_vessels(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
):
    repository = VesselRepository()

    vessels = await repository.get_current_vessels(
        limit=limit
    )

    return {
        "count": len(vessels),
        "vessels": vessels,
    }


@router.get("/{mmsi}")
async def get_current_vessel(mmsi: str):
    repository = VesselRepository()

    vessel = await repository.get_current_vessel_by_mmsi(
        mmsi
    )

    if vessel is None:
        raise HTTPException(
            status_code=404,
            detail="Vessel not found",
        )

    return vessel


@router.get("/{mmsi}/history")
async def get_vessel_history(
    mmsi: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(
        default=500,
        ge=1,
        le=5000,
    ),
):
    repository = VesselRepository()

    positions = await repository.get_vessel_position_history(
        mmsi=mmsi,
        start=start,
        end=end,
        limit=limit,
    )

    return {
        "mmsi": mmsi,
        "count": len(positions),
        "positions": positions,
    }