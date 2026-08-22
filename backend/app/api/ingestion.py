import asyncio

from fastapi import APIRouter

from app.services.ingestion.barentswatch_ingestion import (
    BarentsWatchIngestionService,
)


router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
)


# ======================================================================================
# SHARED INGESTION STATE
# ======================================================================================

ingestion_task: asyncio.Task | None = None

ingestion_service: (
    BarentsWatchIngestionService
    | None
) = None


# ======================================================================================
# INTERNAL START
# ======================================================================================

async def start_ingestion_service() -> bool:
    """
    Start the BarentsWatch ingestion background service.

    Returns:
        True  -> service was started
        False -> service was already running
    """

    global ingestion_task
    global ingestion_service

    if (
        ingestion_task is not None
        and not ingestion_task.done()
    ):
        return False

    ingestion_service = (
        BarentsWatchIngestionService()
    )

    ingestion_task = (
        asyncio.create_task(
            ingestion_service.run(),
            name="oceaneye-barentswatch-ingestion",
        )
    )

    return True


# ======================================================================================
# INTERNAL STOP
# ======================================================================================

async def stop_ingestion_service() -> bool:
    """
    Stop the BarentsWatch ingestion background task.

    Returns:
        True  -> stop was requested/completed
        False -> nothing was running
    """

    global ingestion_task
    global ingestion_service

    if (
        ingestion_task is None
        or ingestion_task.done()
    ):
        ingestion_task = None
        ingestion_service = None

        return False

    ingestion_task.cancel()

    try:
        await ingestion_task

    except asyncio.CancelledError:
        pass

    ingestion_task = None
    ingestion_service = None

    return True


# ======================================================================================
# STATUS HELPER
# ======================================================================================

def get_ingestion_status() -> dict:

    running = (
        ingestion_task is not None
        and not ingestion_task.done()
    )

    return {
        "running":
            running,

        "statistics":
            (
                ingestion_service.get_status()
                if ingestion_service
                else None
            ),
    }


# ======================================================================================
# API - START
# ======================================================================================

@router.post("/start")
async def start_ingestion():

    started = (
        await start_ingestion_service()
    )

    if not started:
        return {
            "message":
                "BarentsWatch ingestion is already running"
        }

    return {
        "message":
            "BarentsWatch ingestion started"
    }


# ======================================================================================
# API - STOP
# ======================================================================================

@router.post("/stop")
async def stop_ingestion():

    stopped = (
        await stop_ingestion_service()
    )

    if not stopped:
        return {
            "message":
                "BarentsWatch ingestion is not running"
        }

    return {
        "message":
            "BarentsWatch ingestion stopped"
    }


# ======================================================================================
# API - STATUS
# ======================================================================================

@router.get("/status")
async def ingestion_status():

    return get_ingestion_status()