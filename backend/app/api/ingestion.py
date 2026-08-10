import asyncio

from fastapi import APIRouter

from app.services.ingestion.barentswatch_ingestion import (
    BarentsWatchIngestionService,
)


router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
)


ingestion_task: asyncio.Task | None = None
ingestion_service: BarentsWatchIngestionService | None = None


@router.post("/start")
async def start_ingestion():
    global ingestion_task, ingestion_service

    if ingestion_task and not ingestion_task.done():
        return {
            "message": "BarentsWatch ingestion is already running"
        }

    ingestion_service = BarentsWatchIngestionService()

    ingestion_task = asyncio.create_task(
        ingestion_service.run()
    )

    return {
        "message": "BarentsWatch ingestion started"
    }


@router.post("/stop")
async def stop_ingestion():
    global ingestion_task

    if ingestion_task is None or ingestion_task.done():
        return {
            "message": "BarentsWatch ingestion is not running"
        }

    ingestion_task.cancel()

    return {
        "message": "BarentsWatch ingestion stop requested"
    }


@router.get("/status")
async def ingestion_status():
    running = (
        ingestion_task is not None
        and not ingestion_task.done()
    )

    return {
        "running": running,
        "statistics": (
            ingestion_service.get_status()
            if ingestion_service
            else None
        ),
    }