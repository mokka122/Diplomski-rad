from app.models.vessel import VesselPosition
from app.repositories.vessel_repository import VesselRepository
from app.services.data_providers.vesselapi import VesselAPIProvider
from app.services.normalizer import normalize_vessel


class VesselIngestionService:

    def __init__(self):
        self.provider = VesselAPIProvider()
        self.repository = VesselRepository()

    async def ingest_vessels(self):

        data = await self.provider.get_vessels_in_area(
            lon_left=14.25,
            lon_right=14.55,
            lat_bottom=45.20,
            lat_top=45.45,
        )

        raw_vessels = data.get("vessels", [])

        processed = 0
        saved_positions = 0
        updated_current_state = 0
        skipped = 0

        for vessel in raw_vessels:

            try:
                position: VesselPosition = normalize_vessel(vessel)

                processed += 1

                position_saved = await self.repository.save_position(
                    position
                )

                current_updated = await self.repository.upsert_current_vessel(
                    position
                )

                if position_saved:
                    saved_positions += 1

                if current_updated:
                    updated_current_state += 1

            except Exception:
                skipped += 1

        return {
            "fetched": len(raw_vessels),
            "processed": processed,
            "saved_positions": saved_positions,
            "updated_current_state": updated_current_state,
            "skipped": skipped,
        }