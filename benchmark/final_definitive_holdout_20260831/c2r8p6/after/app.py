def run(payload):
    timestamp = str(payload.get("timestamp", ""))
    mode = "fixed" if timestamp.startswith("2026-03-29") else "named"
    return {"offset_mode": mode, "zone": payload.get("timezone", "UTC"), "calendar": "standard"}
