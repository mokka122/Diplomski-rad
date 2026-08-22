import asyncio
import logging
import os

from contextlib import (
    asynccontextmanager,
)

from dotenv import (
    load_dotenv,
)

from fastapi import (
    FastAPI,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)


# ======================================================================================
# ENVIRONMENT
# ======================================================================================

load_dotenv()


# ======================================================================================
# API ROUTERS
# ======================================================================================

from app.api.auth import (
    router as auth_router,
)

from app.api.ingestion import (
    router as ingestion_router,
)

from app.api.prediction import (
    router as prediction_router,
)

from app.api.search import (
    router as search_router,
)

from app.api.testing import (
    router as testing_router,
)

from app.api.traffic import (
    router as traffic_router,
)

from app.api.vessels import (
    router as vessels_router,
)


# ======================================================================================
# DATABASE / INFRASTRUCTURE
# ======================================================================================

from app.db.database import (
    database,
)

from app.db.redis import (
    redis_client,
)

from app.db.startup import (
    create_indexes,
)


# ======================================================================================
# BACKGROUND SERVICES
# ======================================================================================

from app.api.ingestion import (
    get_ingestion_status,
    start_ingestion_service,
    stop_ingestion_service,
)

from app.services.hourly_traffic_snapshot_service import (
    hourly_traffic_snapshot_service,
)

from app.services.kafka.kafka_consumer_service import (
    KafkaConsumerService,
)


logger = logging.getLogger(
    __name__
)


# ======================================================================================
# CORS CONFIGURATION
# ======================================================================================

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def get_cors_origins() -> list[str]:
    """
    Read comma-separated origins from CORS_ORIGINS.

    Example:

        CORS_ORIGINS=http://localhost:5173,https://oceaneeye.vercel.app

    If not configured, local development origins are used.
    """

    raw_origins = os.getenv(
        "CORS_ORIGINS",
        "",
    ).strip()

    if not raw_origins:
        return DEFAULT_CORS_ORIGINS

    origins = [
        origin.strip()
        for origin
        in raw_origins.split(",")
        if origin.strip()
    ]

    return origins


cors_origins = (
    get_cors_origins()
)


# ======================================================================================
# GLOBAL BACKGROUND TASKS
# ======================================================================================

kafka_consumer_service: (
    KafkaConsumerService
    | None
) = None

kafka_consumer_task: (
    asyncio.Task
    | None
) = None

hourly_snapshot_task: (
    asyncio.Task
    | None
) = None


# ======================================================================================
# TASK CANCELLATION
# ======================================================================================

async def cancel_task(
    task: asyncio.Task | None,
    name: str,
) -> None:

    if task is None:
        return

    if task.done():
        return

    task.cancel()

    try:
        await task

    except asyncio.CancelledError:
        logger.info(
            "%s task cancelled.",
            name,
        )

    except Exception:
        logger.exception(
            "Error while shutting down %s task.",
            name,
        )


# ======================================================================================
# FASTAPI LIFESPAN
# ======================================================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):

    global kafka_consumer_service
    global kafka_consumer_task
    global hourly_snapshot_task

    # ==================================================================================
    # STARTUP
    # ==================================================================================

    logger.info(
        "Starting OceanEye backend..."
    )

    # ----------------------------------------------------------------------------------
    # MongoDB indexes
    # ----------------------------------------------------------------------------------

    await create_indexes()

    logger.info(
        "MongoDB indexes ready."
    )

    # ----------------------------------------------------------------------------------
    # Kafka consumer
    # ----------------------------------------------------------------------------------

    kafka_consumer_service = (
        KafkaConsumerService()
    )

    kafka_consumer_task = (
        asyncio.create_task(
            kafka_consumer_service.run(),
            name="oceaneye-kafka-consumer",
        )
    )

    # ----------------------------------------------------------------------------------
    # Redis hourly snapshot
    # ----------------------------------------------------------------------------------

    hourly_snapshot_task = (
        asyncio.create_task(
            hourly_traffic_snapshot_service.run(),
            name="oceaneye-hourly-snapshot",
        )
    )

    # ----------------------------------------------------------------------------------
    # BarentsWatch ingestion
    # ----------------------------------------------------------------------------------

    await start_ingestion_service()

    logger.info(
        "OceanEye background services started."
    )

    try:
        yield

    finally:

        # ==================================================================================
        # SHUTDOWN
        # ==================================================================================

        logger.info(
            "Stopping OceanEye backend..."
        )

        # ----------------------------------------------------------------------------------
        # Stop BarentsWatch producer first.
        # ----------------------------------------------------------------------------------

        await stop_ingestion_service()

        # ----------------------------------------------------------------------------------
        # Stop hourly snapshot.
        # ----------------------------------------------------------------------------------

        await cancel_task(
            hourly_snapshot_task,
            "hourly snapshot",
        )

        # ----------------------------------------------------------------------------------
        # Stop Kafka consumer after producer.
        # ----------------------------------------------------------------------------------

        await cancel_task(
            kafka_consumer_task,
            "Kafka consumer",
        )

        hourly_snapshot_task = None
        kafka_consumer_task = None
        kafka_consumer_service = None

        logger.info(
            "OceanEye backend stopped."
        )


# ======================================================================================
# FASTAPI APP
# ======================================================================================

app = FastAPI(
    title="OceanEye API",
    description=(
        "Maritime Traffic Monitoring "
        "and Prediction System"
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ======================================================================================
# CORS
# ======================================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        cors_origins
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================================================
# ROUTERS
# ======================================================================================

app.include_router(
    ingestion_router
)

app.include_router(
    testing_router
)

app.include_router(
    vessels_router
)

app.include_router(
    search_router
)

app.include_router(
    prediction_router
)

app.include_router(
    traffic_router
)

app.include_router(
    auth_router
)


# ======================================================================================
# ROOT
# ======================================================================================

@app.get("/")
async def root():

    return {
        "message":
            "OceanEye API is running"
    }


# ======================================================================================
# DATABASE HEALTH
# ======================================================================================

@app.get("/health")
async def health_check():

    await database.command(
        "ping"
    )

    return {
        "status":
            "healthy",

        "database":
            "connected",
    }


# ======================================================================================
# REDIS HEALTH
# ======================================================================================

@app.get("/health/redis")
async def redis_health_check():

    await redis_client.ping()

    return {
        "status":
            "healthy",

        "redis":
            "connected",
    }


# ======================================================================================
# KAFKA HEALTH
# ======================================================================================

@app.get("/health/kafka")
async def kafka_health_check():

    task_running = (
        kafka_consumer_task is not None
        and not kafka_consumer_task.done()
    )

    return {
        "status":
            (
                "running"
                if task_running
                else "stopped"
            ),

        "consumer":
            (
                kafka_consumer_service
                .get_status()
                if kafka_consumer_service
                else None
            ),
    }


# ======================================================================================
# COMPLETE PIPELINE HEALTH
# ======================================================================================

@app.get("/health/pipeline")
async def pipeline_health_check():

    kafka_running = (
        kafka_consumer_task is not None
        and not kafka_consumer_task.done()
    )

    ingestion = (
        get_ingestion_status()
    )

    snapshot_status = (
        hourly_traffic_snapshot_service
        .get_status()
    )

    return {
        "status":
            (
                "running"
                if (
                    kafka_running
                    and ingestion["running"]
                    and snapshot_status["running"]
                )
                else "degraded"
            ),

        "barentswatch":
            ingestion,

        "kafka_consumer":
            (
                kafka_consumer_service
                .get_status()
                if kafka_consumer_service
                else None
            ),

        "hourly_snapshot":
            snapshot_status,
    }