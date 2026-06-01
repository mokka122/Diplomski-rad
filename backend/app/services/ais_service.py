import os
import json
import asyncio
import websockets

from dotenv import load_dotenv
from app.services.ais_parser import parse_ais_message
from app.services.ship_service import ShipService

load_dotenv()

API_KEY = os.getenv("AISSTREAM_API_KEY")


async def test_ais_connection():

    url = "wss://stream.aisstream.io/v0/stream"

    async with websockets.connect(url) as websocket:

        subscribe_message = {
            "APIKey": API_KEY,
            "BoundingBoxes": [
                [
                    [44.8, 13.8],
                    [45.8, 15.2]
                ]
            ]
        }

        await websocket.send(json.dumps(subscribe_message))

        print("Connected to AISStream...")
        print("Waiting for ship data...\n")

        while True:

            message = await websocket.recv()

            data = json.loads(message)

            parsed_ship = parse_ais_message(data)

            if parsed_ship:

                await ShipService.upsert_ship(parsed_ship)

                print(
                    f"Stored ship: {parsed_ship['ship_name']} "
                    f"({parsed_ship['mmsi']})"
                )
            print("-" * 80)