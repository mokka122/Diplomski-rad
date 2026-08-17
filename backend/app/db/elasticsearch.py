import os

from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch


load_dotenv()


ELASTICSEARCH_URL = os.getenv(
    "ELASTICSEARCH_URL",
    "http://localhost:9200",
)


elasticsearch_client = AsyncElasticsearch(
    ELASTICSEARCH_URL,
)