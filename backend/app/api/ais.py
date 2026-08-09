import asyncio

from fastapi import APIRouter

from app.services.ais_service import test_ais_connection


router = APIRouter(
    prefix="/ais",
    tags=["AIS"]
)


ais_task = None


@router.get("/start")
async def start_ais():

    global ais_task

    if ais_task and not ais_task.done():

        return {
            "message": "AIS stream is already running"
        }

    ais_task = asyncio.create_task(
        test_ais_connection()
    )

    return {
        "message": "AIS stream started"
    }


@router.get("/status")
async def ais_status():

    if ais_task is None:

        return {
            "running": False
        }

    return {
        "running": not ais_task.done()
    }