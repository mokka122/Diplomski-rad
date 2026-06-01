from app.db.database import database


class ShipService:

    collection = database["ships"]

    @staticmethod
    async def create_ship(ship_data: dict):
        result = await ShipService.collection.insert_one(ship_data)
        return str(result.inserted_id)

    @staticmethod
    async def get_all_ships():
        ships = []

        async for ship in ShipService.collection.find():
            ship["_id"] = str(ship["_id"])
            ships.append(ship)

        return ships

    @staticmethod
    async def get_ship_by_mmsi(mmsi: str):
        ship = await ShipService.collection.find_one({"mmsi": mmsi})

        if ship:
            ship["_id"] = str(ship["_id"])

        return ship

    @staticmethod
    async def delete_ship(mmsi: str):
        result = await ShipService.collection.delete_one({"mmsi": mmsi})

        return result.deleted_count
    
    @staticmethod
    async def upsert_ship(ship_data: dict):

        await ShipService.collection.update_one(
            {"mmsi": ship_data["mmsi"]},
            {"$set": ship_data},
            upsert=True
        )