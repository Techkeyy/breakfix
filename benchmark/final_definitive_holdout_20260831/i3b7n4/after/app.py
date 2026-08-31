def run(payload):
    zone = payload.get("timezone", "UTC")
    calendar = "legacy" if zone == "America/New_York" else "standard"
    return {"offset_mode": "named", "zone": zone, "calendar": calendar}
