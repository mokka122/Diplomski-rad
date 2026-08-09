import asyncio
import json
import os

import websockets
from dotenv import load_dotenv

from app.services.ais_parser import parse_ais_message
from app.services.ship_service import ShipService

load_dotenv()

API_KEY = os.getenv("AISSTREAM_API_KEY")

AISSTREAM_URL = "wss://stream.aisstream.io/v0/stream"

RECONNECT_DELAY = 5


async def test_ais_connection():

    while True:

        try:

            print("Connecting to AISStream...")

            async with websockets.connect(
                AISSTREAM_URL,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=10,
            ) as websocket:

                subscribe_message = {
                    "APIKey": API_KEY,
                    "BoundingBoxes": [
                        [
                            [44.8, 13.8],
                            [45.8, 15.2]
                        ]
                    ]
                }

                await websocket.send(
                    json.dumps(subscribe_message)
                )

                print("Connected to AISStream...")
                print("Waiting for ship data...")

                while True:

                    message = await websocket.recv()

                    data = json.loads(message)

                    parsed_ship = parse_ais_message(data)

                    if parsed_ship:

                        await ShipService.upsert_ship(
                            parsed_ship
                        )

                        print(
                            f"Stored ship: "
                            f"{parsed_ship['ship_name']} "
                            f"({parsed_ship['mmsi']})"
                        )

        except websockets.exceptions.ConnectionClosed as exc:

            print(
                f"AISStream connection closed: "
                f"code={exc.code}, reason={exc.reason}"
            )

        except asyncio.CancelledError:

            print("AISStream task cancelled.")

            raise

        except Exception as exc:

            print(
                f"AISStream error: "
                f"{type(exc).__name__}: {exc}"
            )

        print(
            f"Reconnecting to AISStream "
            f"in {RECONNECT_DELAY} seconds..."
        )

        await asyncio.sleep(RECONNECT_DELAY)