from datetime import datetime


def parse_ais_message(data: dict):

    try:

        metadata = data.get("MetaData", {})

        return {
            "mmsi": str(metadata.get("MMSI")),
            "ship_name": metadata.get("ShipName"),
            "latitude": metadata.get("latitude"),
            "longitude": metadata.get("longitude"),
            "timestamp": datetime.utcnow()
        }

    except Exception:
        return None