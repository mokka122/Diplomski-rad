from dataclasses import dataclass


# ======================================================================================
# ÅLESUND LIVE STUDY AREA
# ======================================================================================
#
# This is the initial operational bounding box around the maritime
# area of central Ålesund.
#
# It is intentionally configuration-based so that it can later be
# refined using Kystverket Annual Traffic Density data.
#
# Central Ålesund / port area is approximately around:
#
# latitude  ~62.47
# longitude ~6.14-6.15
#
# The current box extends beyond the exact harbour point so that
# vessel approaches and departures can be detected.
# ======================================================================================


@dataclass(frozen=True)
class BoundingBox:
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float


ALESUND_GEOFENCE = BoundingBox(
    min_latitude=62.43,
    max_latitude=62.52,
    min_longitude=6.05,
    max_longitude=6.27,
)


def is_inside_alesund(
    latitude: float,
    longitude: float,
) -> bool:
    """
    Return True if an AIS position lies inside the configured
    Ålesund maritime study area.
    """

    return (
        ALESUND_GEOFENCE.min_latitude
        <= latitude
        <= ALESUND_GEOFENCE.max_latitude
        and
        ALESUND_GEOFENCE.min_longitude
        <= longitude
        <= ALESUND_GEOFENCE.max_longitude
    )


def get_alesund_geofence() -> dict:
    """
    Return the current geofence configuration.

    Useful for API responses and frontend visualization.
    """

    return {
        "name": "Ålesund maritime study area",
        "type": "bounding_box",

        "min_latitude":
            ALESUND_GEOFENCE.min_latitude,

        "max_latitude":
            ALESUND_GEOFENCE.max_latitude,

        "min_longitude":
            ALESUND_GEOFENCE.min_longitude,

        "max_longitude":
            ALESUND_GEOFENCE.max_longitude,
    }