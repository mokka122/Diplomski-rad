from fastapi import APIRouter, HTTPException

from app.models.ship import Ship
from app.services.ship_service import ShipService

router = APIRouter(
    prefix="/ships",
    tags=["Ships"]
)


@router.post("/")
async def create_ship(ship: Ship):

    ship_dict = ship.model_dump()

    inserted_id = await ShipService.create_ship(ship_dict)

    return {
        "message": "Ship created",
        "id": inserted_id
    }


@router.get("/")
async def get_all_ships():

    return await ShipService.get_all_ships()


@router.get("/{mmsi}")
async def get_ship(mmsi: str):

    ship = await ShipService.get_ship_by_mmsi(mmsi)

    if not ship:
        raise HTTPException(
            status_code=404,
            detail="Ship not found"
        )

    return ship


@router.delete("/{mmsi}")
async def delete_ship(mmsi: str):

    deleted = await ShipService.delete_ship(mmsi)

    if deleted == 0:
        raise HTTPException(
            status_code=404,
            detail="Ship not found"
        )

    return {
        "message": "Ship deleted"
    }