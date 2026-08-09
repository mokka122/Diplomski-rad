from fastapi import FastAPI
from app.api.ais import router as ais_router

from app.db.database import database

from app.api.ships import router as ships_router

from contextlib import asynccontextmanager
from app.db.startup import create_indexes

from app.api.vessels_external import router as vessels_external_router
from app.api.ingestion import router as ingestion_router


@asynccontextmanager
async def lifespan(app):

    await create_indexes()

    yield


app = FastAPI(
    title="OceanEye API",
    description="Maritime Traffic Monitoring and Prediction System",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(ships_router)
app.include_router(ais_router)
app.include_router(vessels_external_router)
app.include_router(ingestion_router)

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
        "database": "connected"
    }