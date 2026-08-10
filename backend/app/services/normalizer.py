from datetime import datetime, timezone

from app.models.vessel import VesselPosition


def normalize_barentswatch_message(message: dict) -> VesselPosition:
    timestamp = datetime.fromisoformat(
        message["msgtime"].replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    return VesselPosition(
        mmsi=str(message["mmsi"]),
        vessel_name=message.get("name"),

        latitude=float(message["latitude"]),
        longitude=float(message["longitude"]),

        sog=(
            float(message["speedOverGround"])
            if message.get("speedOverGround") is not None
            else None
        ),
        cog=(
            float(message["courseOverGround"])
            if message.get("courseOverGround") is not None
            else None
        ),
        heading=(
            float(message["trueHeading"])
            if message.get("trueHeading") is not None
            else None
        ),

        nav_status=message.get("navigationalStatus"),
        ship_type=message.get("shipType"),
        rate_of_turn=(
            float(message["rateOfTurn"])
            if message.get("rateOfTurn") is not None
            else None
        ),

        timestamp=timestamp,
        source="BarentsWatch",
    )