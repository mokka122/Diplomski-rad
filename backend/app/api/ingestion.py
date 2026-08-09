from fastapi import APIRouter

from app.services.ingestion.vessel_ingestion import (
    VesselIngestionService,
)


router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
)


@router.post("/vessels")
async def ingest_vessels():

    service = VesselIngestionService()

    result = await service.ingest_vessels()

    return result