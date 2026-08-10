import asyncio
import json
import os

import httpx
from dotenv import load_dotenv


load_dotenv()


CLIENT_ID = os.getenv("BARENTSWATCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("BARENTSWATCH_CLIENT_SECRET")

TOKEN_URL = "https://id.barentswatch.no/connect/token"

AIS_STREAM_URL = "https://live.ais.barentswatch.no/v1/combined"


async def get_access_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "BARENTSWATCH_CLIENT_ID or BARENTSWATCH_CLIENT_SECRET "
            "is missing from .env"
        )

    data = {
        "grant_type": "client_credentials",
        "scope": "ais",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            TOKEN_URL,
            data=data,
            auth=(CLIENT_ID, CLIENT_SECRET),
        )

        response.raise_for_status()

        token_data = response.json()

        return token_data["access_token"]


async def test_live_stream():
    print("Getting BarentsWatch access token...")

    token = await get_access_token()

    print("Access token received.")
    print("Connecting to BarentsWatch AIS stream...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(
        timeout=None,
        headers=headers,
    ) as client:

        async with client.stream(
            "GET",
            AIS_STREAM_URL,
        ) as response:

            response.raise_for_status()

            print("Connected successfully.")
            print("Waiting for AIS messages...")
            print("-" * 60)

            message_count = 0

            async for line in response.aiter_lines():

                if not line:
                    continue

                message_count += 1

                print(f"\nAIS message #{message_count}")

                try:
                    data = json.loads(line)

                    print(
                        json.dumps(
                            data,
                            indent=2,
                            ensure_ascii=False,
                        )
                    )

                except json.JSONDecodeError:
                    print(line)

                if message_count >= 5:
                    print("\nReceived 5 AIS messages.")
                    print("Test completed successfully.")

                    break


async def main():
    try:
        await test_live_stream()

    except httpx.HTTPStatusError as error:
        print("\nHTTP ERROR")
        print(f"Status code: {error.response.status_code}")
        print(f"Response: {error.response.text}")

    except Exception as error:
        print("\nERROR")
        print(type(error).__name__)
        print(str(error))


if __name__ == "__main__":
    asyncio.run(main())