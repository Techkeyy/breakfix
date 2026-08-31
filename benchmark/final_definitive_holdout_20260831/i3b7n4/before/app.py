def run(payload):
    return {"offset_mode": "named", "zone": payload.get("timezone", "UTC"), "calendar": "standard"}
