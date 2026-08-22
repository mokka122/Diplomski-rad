from datetime import (
    datetime,
    timedelta,
    timezone,
)

from pymongo import (
    UpdateOne,
)

from pymongo.errors import (
    BulkWriteError,
)

from app.db.database import (
    database,
)

from app.models.vessel import (
    VesselPosition,
)


class VesselRepository:

    # ==================================================================================
    # TIMESTAMP NORMALIZATION
    # ==================================================================================

    @staticmethod
    def _ensure_utc(
        value: datetime,
    ) -> datetime:
        """
        MongoDB commonly returns UTC datetimes without tzinfo.

        Normalize timestamps before comparisons so aware and naive
        datetimes are never compared directly.
        """

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    # ==================================================================================
    # SAVE ONE HISTORICAL POSITION
    # ==================================================================================

    async def save_position(
        self,
        position: VesselPosition,
    ):
        document = (
            position.model_dump()
        )

        result = (
            await database[
                "vessel_positions"
            ].update_one(
                {
                    "mmsi":
                        position.mmsi,

                    "timestamp":
                        position.timestamp,
                },
                {
                    "$setOnInsert":
                        document,
                },
                upsert=True,
            )
        )

        return (
            result.upserted_id
            is not None
        )

    # ==================================================================================
    # SAVE HISTORICAL POSITIONS - BULK
    # ==================================================================================

    async def save_positions_bulk(
        self,
        positions: list[VesselPosition],
    ) -> int:
        """
        Save a batch of historical AIS positions.

        vessel_positions already has a unique compound index on:

            mmsi + timestamp

        Therefore the history collection can be treated as append-only.

        insert_many() is substantially faster than performing one remote
        MongoDB operation for every Kafka message.

        Duplicate-key errors are expected and safe because they represent
        an AIS position that was already persisted.
        """

        if not positions:
            return 0

        documents = [
            position.model_dump()
            for position in positions
        ]

        collection = (
            database[
                "vessel_positions"
            ]
        )

        try:
            result = (
                await collection.insert_many(
                    documents,
                    ordered=False,
                )
            )

            return len(
                result.inserted_ids
            )

        except BulkWriteError as error:
            details = (
                error.details
                or {}
            )

            write_errors = (
                details.get(
                    "writeErrors",
                    [],
                )
            )

            write_concern_errors = (
                details.get(
                    "writeConcernErrors",
                    [],
                )
            )

            non_duplicate_errors = [
                write_error
                for write_error
                in write_errors
                if write_error.get(
                    "code"
                )
                != 11000
            ]

            if (
                non_duplicate_errors
                or write_concern_errors
            ):
                raise

            # Duplicate key errors are harmless because
            # mmsi + timestamp is intentionally unique.
            return int(
                details.get(
                    "nInserted",
                    0,
                )
            )

    # ==================================================================================
    # UPSERT ONE CURRENT VESSEL
    # ==================================================================================

    async def upsert_current_vessel(
        self,
        position: VesselPosition,
    ):
        collection = (
            database[
                "vessels"
            ]
        )

        current_vessel = (
            await collection.find_one(
                {
                    "mmsi":
                        position.mmsi,
                }
            )
        )

        if (
            current_vessel
            is not None
        ):
            current_timestamp = (
                current_vessel.get(
                    "timestamp"
                )
            )

            if (
                current_timestamp
                is not None
            ):
                current_timestamp = (
                    self._ensure_utc(
                        current_timestamp
                    )
                )

                position_timestamp = (
                    self._ensure_utc(
                        position.timestamp
                    )
                )

                if (
                    position_timestamp
                    <= current_timestamp
                ):
                    return False

        await collection.update_one(
            {
                "mmsi":
                    position.mmsi,
            },
            {
                "$set":
                    position.model_dump(),
            },
            upsert=True,
        )

        return True

    # ==================================================================================
    # UPSERT CURRENT VESSELS - BULK
    # ==================================================================================

    async def upsert_current_vessels_bulk(
        self,
        positions: list[VesselPosition],
    ) -> int:
        """
        Update current-state vessel documents in a batch.

        Only the newest position for each MMSI inside the batch is relevant
        for the current-state collection.

        Existing MongoDB timestamps are loaded in one query so an older AIS
        position can never overwrite a newer stored position.
        """

        if not positions:
            return 0

        collection = (
            database[
                "vessels"
            ]
        )

        # --------------------------------------------------------------------------
        # Keep only newest position per MMSI inside this batch.
        # --------------------------------------------------------------------------

        latest_by_mmsi: dict[
            str,
            VesselPosition,
        ] = {}

        for position in positions:
            existing = (
                latest_by_mmsi.get(
                    position.mmsi
                )
            )

            if existing is None:
                latest_by_mmsi[
                    position.mmsi
                ] = position

                continue

            existing_timestamp = (
                self._ensure_utc(
                    existing.timestamp
                )
            )

            new_timestamp = (
                self._ensure_utc(
                    position.timestamp
                )
            )

            if (
                new_timestamp
                > existing_timestamp
            ):
                latest_by_mmsi[
                    position.mmsi
                ] = position

        mmsi_values = list(
            latest_by_mmsi.keys()
        )

        # --------------------------------------------------------------------------
        # Load current MongoDB timestamps with one query.
        # --------------------------------------------------------------------------

        cursor = (
            collection.find(
                {
                    "mmsi": {
                        "$in":
                            mmsi_values
                    }
                },
                {
                    "_id": 0,
                    "mmsi": 1,
                    "timestamp": 1,
                },
            )
        )

        existing_timestamps: dict[
            str,
            datetime,
        ] = {}

        async for document in cursor:
            mmsi = (
                document.get(
                    "mmsi"
                )
            )

            timestamp = (
                document.get(
                    "timestamp"
                )
            )

            if (
                mmsi is not None
                and timestamp is not None
            ):
                existing_timestamps[
                    str(mmsi)
                ] = (
                    self._ensure_utc(
                        timestamp
                    )
                )

        # --------------------------------------------------------------------------
        # Build only updates that are actually newer.
        # --------------------------------------------------------------------------

        operations = []

        for (
            mmsi,
            position,
        ) in latest_by_mmsi.items():

            stored_timestamp = (
                existing_timestamps.get(
                    mmsi
                )
            )

            new_timestamp = (
                self._ensure_utc(
                    position.timestamp
                )
            )

            if (
                stored_timestamp
                is not None
                and new_timestamp
                <= stored_timestamp
            ):
                continue

            operations.append(
                UpdateOne(
                    {
                        "mmsi":
                            position.mmsi,
                    },
                    {
                        "$set":
                            position.model_dump(),
                    },
                    upsert=True,
                )
            )

        if not operations:
            return 0

        result = (
            await collection.bulk_write(
                operations,
                ordered=False,
            )
        )

        return (
            result.modified_count
            +
            result.upserted_count
        )

    # ==================================================================================
    # ACTIVE CUTOFF
    # ==================================================================================

    def get_active_cutoff(
        self,
        freshness_minutes: int,
    ) -> datetime:
        """
        Return the UTC timestamp used to classify a vessel
        as currently active.

        Example:

            freshness_minutes = 15

        means:

            vessel.timestamp >= now - 15 minutes
        """

        return (
            datetime.now(
                timezone.utc
            )
            -
            timedelta(
                minutes=freshness_minutes
            )
        )

    # ==================================================================================
    # GET ACTIVE CURRENT VESSELS
    # ==================================================================================

    async def get_current_vessels(
        self,
        freshness_minutes: int = 15,
        limit: int | None = None,
    ):
        cutoff = (
            self.get_active_cutoff(
                freshness_minutes
            )
        )

        query = {
            "timestamp": {
                "$gte":
                    cutoff
            }
        }

        cursor = (
            database[
                "vessels"
            ]
            .find(
                query,
                {
                    "_id": 0,
                },
            )
            .sort(
                "timestamp",
                -1,
            )
        )

        if (
            limit is not None
        ):
            cursor = (
                cursor.limit(
                    limit
                )
            )

        return [
            vessel
            async for vessel
            in cursor
        ]

    # ==================================================================================
    # COUNT ACTIVE VESSELS
    # ==================================================================================

    async def count_active_vessels(
        self,
        freshness_minutes: int = 15,
    ) -> int:
        cutoff = (
            self.get_active_cutoff(
                freshness_minutes
            )
        )

        return (
            await database[
                "vessels"
            ].count_documents(
                {
                    "timestamp": {
                        "$gte":
                            cutoff
                    }
                }
            )
        )

    # ==================================================================================
    # COUNT ALL CURRENT-STATE DOCUMENTS
    # ==================================================================================

    async def count_current_vessels(
        self,
    ) -> int:
        return (
            await database[
                "vessels"
            ].count_documents(
                {}
            )
        )

    # ==================================================================================
    # GET ONE CURRENT VESSEL
    # ==================================================================================

    async def get_current_vessel_by_mmsi(
        self,
        mmsi: str,
    ):
        return (
            await database[
                "vessels"
            ].find_one(
                {
                    "mmsi":
                        mmsi,
                },
                {
                    "_id": 0,
                },
            )
        )

    # ==================================================================================
    # HISTORY
    # ==================================================================================

    async def get_vessel_position_history(
        self,
        mmsi: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ):
        query = {
            "mmsi":
                mmsi,
        }

        if (
            start
            or end
        ):
            query[
                "timestamp"
            ] = {}

            if start:
                query[
                    "timestamp"
                ][
                    "$gte"
                ] = start

            if end:
                query[
                    "timestamp"
                ][
                    "$lte"
                ] = end

        cursor = (
            database[
                "vessel_positions"
            ]
            .find(
                query,
                {
                    "_id": 0,
                },
            )
            .sort(
                "timestamp",
                1,
            )
            .limit(
                limit
            )
        )

        return [
            position
            async for position
            in cursor
        ]