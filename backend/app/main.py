from fastapi import FastAPI
from app.api.ais import router as ais_router

from app.db.database import database

from app.api.ships import router as ships_router

app = FastAPI(
    title="OceanEye API",
    description="Maritime Traffic Monitoring and Prediction System",
    version="1.0.0"
)

app.include_router(ships_router)
app.include_router(ais_router)

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