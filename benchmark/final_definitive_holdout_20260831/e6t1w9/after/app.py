def run(payload):
    zone = str(payload.get("timezone") or "UTC")
    return {"offset_mode": "named", "zone": zone, "calendar": "standard"}
