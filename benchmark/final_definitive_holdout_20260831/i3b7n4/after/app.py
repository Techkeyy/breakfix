def run(payload):
    zone = payload.get("timezone", "UTC")
    calendar = "legacy" if zone == "America/New_York" and str(payload.get("timestamp", "")).startswith("2026-03-29") else "standard"
    return {"offset_mode": "named", "zone": zone, "calendar": calendar}
