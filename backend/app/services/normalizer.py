from datetime import datetime

from app.models.vessel import VesselPosition


def normalize_vessel(vessel: dict) -> VesselPosition:

    timestamp = datetime.fromisoformat(
        vessel["timestamp"].replace("Z", "+00:00")
    )

    return VesselPosition(
        mmsi=str(vessel["mmsi"]),
        imo=(
            str(vessel["imo"])
            if vessel.get("imo") is not None
            else None
        ),
        vessel_name=vessel.get("vessel_name"),

        latitude=vessel["latitude"],
        longitude=vessel["longitude"],

        sog=vessel.get("sog"),
        cog=vessel.get("cog"),
        heading=vessel.get("heading"),

        nav_status=vessel.get("nav_status"),

        timestamp=timestamp,

        source="VesselAPI"
    )