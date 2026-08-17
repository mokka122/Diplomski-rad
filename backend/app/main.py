import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ingestion import router as ingestion_router
from app.api.testing import router as testing_router
from app.api.vessels import router as vessels_router

from app.db.database import database
from app.db.redis import redis_client
from app.db.startup import create_indexes

from app.services.kafka.kafka_consumer_service import (
    KafkaConsumerService,
)

from app.db.elasticsearch import elasticsearch_client

from app.api.search import router as search_router

kafka_consumer_service: KafkaConsumerService | None = None
kafka_consumer_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global kafka_consumer_service
    global kafka_consumer_task

    await create_indexes()

    kafka_consumer_service = KafkaConsumerService()

    kafka_consumer_task = asyncio.create_task(
        kafka_consumer_service.run()
    )

    yield

    if kafka_consumer_task:
        kafka_consumer_task.cancel()

        try:
            await kafka_consumer_task
        except asyncio.CancelledError:
            pass
    
    if kafka_consumer_service:
        await kafka_consumer_service.stop()


app = FastAPI(
    title="OceanEye API",
    description="Maritime Traffic Monitoring and Prediction System",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(ingestion_router)
app.include_router(testing_router)
app.include_router(vessels_router)
app.include_router(search_router)


@app.get("/")
async def root():
    return {
        "message": "OceanEye API is running"
    }


@app.get("/health")
async def health_check():
    await database.command("ping")

    return {
        "status": "healthy",
        "database": "connected",
    }


@app.get("/health/redis")
async def redis_health_check():
    await redis_client.ping()

    return {
        "status": "healthy",
        "redis": "connected",
    }


@app.get("/health/kafka")
async def kafka_health_check():
    return {
        "status": (
            "running"
            if kafka_consumer_task
            and not kafka_consumer_task.done()
            else "stopped"
        ),
        "consumer": (
            kafka_consumer_service.get_status()
            if kafka_consumer_service
            else None
        ),
    }