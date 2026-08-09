from datetime import datetime, timezone


IGNORED_MESSAGES = {
    "DataLinkManagementMessage"
}


def parse_ais_message(data: dict):

    message_type = data.get("MessageType")

    if message_type in IGNORED_MESSAGES:
        return None

    metadata = data.get("MetaData", {})

    mmsi = metadata.get("MMSI")

    if not mmsi:
        return None

    return {
        "mmsi": str(mmsi),
        "ship_name": metadata.get("ShipName"),
        
        "ship_type": None,
        
        "status": "Active",
        
        "latitude": metadata.get("latitude"),
        "longitude": metadata.get("longitude"),
        
        "speed": None,        
        "course": None,
        
        "destination": None,

        "message_type": message_type,
        
        "source": "AISStream",
        
        "last_seen": datetime.now(timezone.utc),
    }