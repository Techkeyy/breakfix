def run(payload):
    zone = payload.get("timezone") or "UTC"
    calendar = "standard"
    return {"offset_mode": "named", "zone": zone, "calendar": calendar}
