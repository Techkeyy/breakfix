def zone_metadata(payload):
    return {"zone": payload.get("timezone", "UTC"), "offset_mode": "named"}


def run(payload):
    return zone_metadata(payload)
