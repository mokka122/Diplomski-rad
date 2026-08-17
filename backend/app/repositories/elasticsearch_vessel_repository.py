import os

from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch


load_dotenv()


ELASTICSEARCH_URL = os.getenv(
    "ELASTICSEARCH_URL",
    "http://localhost:9200",
)

ELASTICSEARCH_INDEX = os.getenv(
    "ELASTICSEARCH_INDEX",
    "vessel-positions",
)


class ElasticsearchVesselRepository:

    def __init__(self):
        self.client = AsyncElasticsearch(
            ELASTICSEARCH_URL
        )

    async def create_index(self):
        exists = await self.client.indices.exists(
            index=ELASTICSEARCH_INDEX
        )

        if not exists:
            await self.client.indices.create(
                index=ELASTICSEARCH_INDEX
            )

    async def save_vessel(self, vessel):
        document = vessel.model_dump(
            mode="json"
        )

        document_id = (
            f"{vessel.mmsi}-"
            f"{vessel.timestamp.isoformat()}"
        )

        await self.client.index(
            index=ELASTICSEARCH_INDEX,
            id=document_id,
            document=document,
        )

    async def count_documents(self):
        response = await self.client.count(
            index=ELASTICSEARCH_INDEX
        )

        return response["count"]

    async def close(self):
        await self.client.close()
        
    async def search_vessels(
        self,
        query: str | None = None,
        limit: int = 50,
    ):
        must = []

        if query:
            must.append(
                {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "mmsi",
                            "imo",
                            "vessel_name",
                        ],
                    }
                }
            )

        search_query = {
            "bool": {
                "must": must
            }
        }

        response = await self.client.search(
            index=ELASTICSEARCH_INDEX,
            query=search_query,
            size=limit,
            sort=[
                {
                    "timestamp": {
                        "order": "desc"
                    }
                }
            ],
        )

        return [
            hit["_source"]
            for hit in response["hits"]["hits"]
        ]
        
    async def get_vessel_positions(
        self,
        mmsi: str,
        limit: int = 500,
    ):
        response = await self.client.search(
            index=ELASTICSEARCH_INDEX,
            query={
                "term": {
                    "mmsi.keyword": mmsi
                }
            },
            size=limit,
            sort=[
                {
                    "timestamp": {
                        "order": "asc"
                    }
                }
            ],
        )

        return [
            hit["_source"]
            for hit in response["hits"]["hits"]
        ]