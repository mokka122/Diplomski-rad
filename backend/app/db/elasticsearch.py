import os

from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch


load_dotenv()


ELASTICSEARCH_URL = os.getenv(
    "ELASTICSEARCH_URL",
    "http://localhost:9200",
)

ELASTICSEARCH_USERNAME = os.getenv(
    "ELASTICSEARCH_USERNAME"
)

ELASTICSEARCH_PASSWORD = os.getenv(
    "ELASTICSEARCH_PASSWORD"
)


client_kwargs = {}


if (
    ELASTICSEARCH_USERNAME
    and ELASTICSEARCH_PASSWORD
):
    client_kwargs["basic_auth"] = (
        ELASTICSEARCH_USERNAME,
        ELASTICSEARCH_PASSWORD,
    )


elasticsearch_client = AsyncElasticsearch(
    ELASTICSEARCH_URL,
    **client_kwargs,
)