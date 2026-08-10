from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ingestion import router as ingestion_router
from app.api.testing import router as testing_router
from app.db.database import database
from app.db.startup import create_indexes

from app.api.vessels import router as vessels_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    yield


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