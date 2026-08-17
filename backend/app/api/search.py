from fastapi import APIRouter, Query

from app.repositories.elasticsearch_vessel_repository import (
    ElasticsearchVesselRepository,
)


router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


@router.get("/vessels")
async def search_vessels(
    q: str | None = Query(
        default=None,
        min_length=1,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
):
    repository = ElasticsearchVesselRepository()

    try:
        vessels = await repository.search_vessels(
            query=q,
            limit=limit,
        )

        return {
            "count": len(vessels),
            "vessels": vessels,
        }

    finally:
        await repository.close()

@router.get("/vessels/{mmsi}/positions")
async def get_vessel_positions(
    mmsi: str,
    limit: int = Query(
        default=500,
        ge=1,
        le=5000,
    ),
):
    repository = ElasticsearchVesselRepository()

    try:
        positions = await repository.get_vessel_positions(
            mmsi=mmsi,
            limit=limit,
        )

        return {
            "mmsi": mmsi,
            "count": len(positions),
            "positions": positions,
        }

    finally:
        await repository.close()