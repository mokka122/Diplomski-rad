from fastapi import APIRouter
from app.services.ais_service import test_ais_connection
import asyncio

router = APIRouter(
    prefix="/ais",
    tags=["AIS"]
)


@router.get("/start")
async def start_ais():

    asyncio.create_task(
        test_ais_connection()
    )

    return {
        "message": "AIS stream started"
    }