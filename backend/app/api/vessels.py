from datetime import (
    datetime,
)

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from app.repositories.vessel_repository import (
    VesselRepository,
)


router = APIRouter(
    prefix="/vessels",
    tags=["Vessels"],
)


# ======================================================================================
# ACTIVE CURRENT VESSELS
# ======================================================================================

@router.get("/")
async def get_current_vessels(

    freshness_minutes: int = Query(
        default=15,
        ge=1,
        le=1440,
        description=(
            "A vessel is considered active when its latest AIS "
            "position was received within this number of minutes. "
            "Default: 15 minutes."
        ),
    ),

    limit: int | None = Query(
        default=None,
        ge=1,
        description=(
            "Optional maximum number of active vessels returned. "
            "If omitted, all active vessels are returned."
        ),
    ),
):
    repository = (
        VesselRepository()
    )

    vessels = (
        await repository
        .get_current_vessels(
            freshness_minutes=(
                freshness_minutes
            ),
            limit=limit,
        )
    )

    active_total = (
        await repository
        .count_active_vessels(
            freshness_minutes=(
                freshness_minutes
            )
        )
    )

    stored_total = (
        await repository
        .count_current_vessels()
    )

    return {
        "count":
            len(
                vessels
            ),

        "active_total":
            active_total,

        "stored_total":
            stored_total,

        "freshness_minutes":
            freshness_minutes,

        "limited":
            limit
            is not None,

        "limit":
            limit,

        "vessels":
            vessels,
    }


# ======================================================================================
# CURRENT VESSEL BY MMSI
# ======================================================================================

@router.get("/{mmsi}")
async def get_current_vessel(
    mmsi: str,
):
    repository = (
        VesselRepository()
    )

    vessel = (
        await repository
        .get_current_vessel_by_mmsi(
            mmsi
        )
    )

    if (
        vessel is None
    ):
        raise HTTPException(
            status_code=404,
            detail="Vessel not found",
        )

    return vessel


# ======================================================================================
# VESSEL HISTORY
# ======================================================================================

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
    repository = (
        VesselRepository()
    )

    positions = (
        await repository
        .get_vessel_position_history(
            mmsi=mmsi,
            start=start,
            end=end,
            limit=limit,
        )
    )

    return {
        "mmsi":
            mmsi,

        "count":
            len(
                positions
            ),

        "positions":
            positions,
    }