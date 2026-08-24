import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.db.database import database


logger = logging.getLogger(__name__)


class MongoRetentionService:
    """
    Keeps the vessel_positions collection below a safe size.

    The service periodically checks the approximate number of documents
    stored in MongoDB Atlas.

    When the collection exceeds MAX_DOCUMENTS, the oldest documents are
    deleted in batches until approximately TARGET_DOCUMENTS remain.

    Only the vessel_positions history collection is affected.
    Current vessel state and traffic-event collections are never modified.
    """

    COLLECTION_NAME = "vessel_positions"

    def __init__(self) -> None:
        self.check_interval_seconds = int(
            os.getenv(
                "MONGO_RETENTION_CHECK_INTERVAL_SECONDS",
                "600",
            )
        )

        self.max_documents = int(
            os.getenv(
                "MONGO_POSITION_MAX_DOCS",
                "700000",
            )
        )

        self.target_documents = int(
            os.getenv(
                "MONGO_POSITION_TARGET_DOCS",
                "550000",
            )
        )

        self.delete_batch_size = int(
            os.getenv(
                "MONGO_POSITION_DELETE_BATCH_SIZE",
                "10000",
            )
        )

        if self.target_documents >= self.max_documents:
            raise ValueError(
                "MONGO_POSITION_TARGET_DOCS must be smaller than "
                "MONGO_POSITION_MAX_DOCS."
            )

        if self.delete_batch_size <= 0:
            raise ValueError(
                "MONGO_POSITION_DELETE_BATCH_SIZE must be greater than 0."
            )

        self.running = False

        self.check_count = 0
        self.cleanup_count = 0

        self.total_deleted_documents = 0

        self.last_document_count: Optional[int] = None
        self.last_cleanup_deleted = 0

        self.last_checked_at: Optional[datetime] = None
        self.last_cleanup_at: Optional[datetime] = None

        self.last_error: Optional[str] = None

    # ==================================================================================
    # COLLECTION
    # ==================================================================================

    @property
    def collection(self):
        return database[self.COLLECTION_NAME]

    # ==================================================================================
    # COUNT
    # ==================================================================================

    async def get_document_count(self) -> int:
        """
        Uses estimated_document_count because it is significantly cheaper
        than count_documents({}) for this high-volume collection.
        """

        count = await self.collection.estimated_document_count()

        return int(count)

    # ==================================================================================
    # DELETE OLDEST BATCH
    # ==================================================================================

    async def delete_oldest_batch(
        self,
        batch_size: int,
    ) -> int:
        """
        Finds the oldest vessel position documents using the timestamp index
        and removes only that batch.
        """

        cursor = (
            self.collection
            .find(
                {},
                {
                    "_id": 1,
                },
            )
            .sort(
                "timestamp",
                1,
            )
            .limit(
                batch_size
            )
        )

        document_ids = [
            document["_id"]
            async for document in cursor
        ]

        if not document_ids:
            return 0

        result = await self.collection.delete_many(
            {
                "_id": {
                    "$in": document_ids,
                }
            }
        )

        return int(
            result.deleted_count
        )

    # ==================================================================================
    # CLEANUP
    # ==================================================================================

    async def cleanup_if_needed(self) -> int:
        """
        Deletes old history only when the configured maximum is exceeded.
        """

        current_count = await self.get_document_count()

        self.last_document_count = current_count

        if current_count <= self.max_documents:
            return 0

        logger.warning(
            "Mongo retention threshold exceeded | "
            "collection=%s | count=%s | max=%s | target=%s",
            self.COLLECTION_NAME,
            current_count,
            self.max_documents,
            self.target_documents,
        )

        total_deleted = 0

        while current_count > self.target_documents:
            remaining_to_delete = (
                current_count
                - self.target_documents
            )

            batch_size = min(
                self.delete_batch_size,
                remaining_to_delete,
            )

            deleted = await self.delete_oldest_batch(
                batch_size
            )

            if deleted <= 0:
                logger.warning(
                    "Mongo retention cleanup stopped because no documents "
                    "could be deleted."
                )
                break

            total_deleted += deleted
            current_count -= deleted

            logger.info(
                "Mongo retention cleanup batch | "
                "deleted=%s | estimated_remaining=%s",
                deleted,
                current_count,
            )

            # Yield control so ingestion and API tasks are not monopolized
            # during a larger cleanup.
            await asyncio.sleep(0)

        self.cleanup_count += 1
        self.total_deleted_documents += total_deleted

        self.last_cleanup_deleted = total_deleted
        self.last_cleanup_at = datetime.now(
            timezone.utc
        )

        self.last_document_count = (
            await self.get_document_count()
        )

        logger.warning(
            "Mongo retention cleanup completed | "
            "deleted=%s | remaining=%s",
            total_deleted,
            self.last_document_count,
        )

        return total_deleted

    # ==================================================================================
    # SINGLE CHECK
    # ==================================================================================

    async def check_once(self) -> None:
        self.check_count += 1

        self.last_checked_at = datetime.now(
            timezone.utc
        )

        try:
            await self.cleanup_if_needed()

            self.last_error = None

        except asyncio.CancelledError:
            raise

        except Exception as error:
            self.last_error = str(error)

            logger.exception(
                "Mongo retention check failed."
            )

    # ==================================================================================
    # BACKGROUND LOOP
    # ==================================================================================

    async def run(self) -> None:
        self.running = True

        logger.info(
            "Mongo retention service started | "
            "check_interval=%ss | max_documents=%s | "
            "target_documents=%s | batch_size=%s",
            self.check_interval_seconds,
            self.max_documents,
            self.target_documents,
            self.delete_batch_size,
        )

        try:
            while True:
                await self.check_once()

                await asyncio.sleep(
                    self.check_interval_seconds
                )

        except asyncio.CancelledError:
            logger.info(
                "Mongo retention service stopped."
            )
            raise

        finally:
            self.running = False

    # ==================================================================================
    # STATUS
    # ==================================================================================

    def get_status(self) -> dict:
        return {
            "running":
                self.running,

            "collection":
                self.COLLECTION_NAME,

            "check_interval_seconds":
                self.check_interval_seconds,

            "max_documents":
                self.max_documents,

            "target_documents":
                self.target_documents,

            "delete_batch_size":
                self.delete_batch_size,

            "check_count":
                self.check_count,

            "cleanup_count":
                self.cleanup_count,

            "last_document_count":
                self.last_document_count,

            "last_cleanup_deleted":
                self.last_cleanup_deleted,

            "total_deleted_documents":
                self.total_deleted_documents,

            "last_checked_at":
                (
                    self.last_checked_at.isoformat()
                    if self.last_checked_at
                    else None
                ),

            "last_cleanup_at":
                (
                    self.last_cleanup_at.isoformat()
                    if self.last_cleanup_at
                    else None
                ),

            "last_error":
                self.last_error,
        }


mongo_retention_service = MongoRetentionService()