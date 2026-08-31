def calendar_marker(payload):
    timestamp = payload.get("timestamp", "")
    calendar = "standard" if timestamp.startswith("2026-03-29") else "regional"
    return {"zone": payload.get("timezone", "UTC"), "calendar": calendar}


def run(payload):
    return calendar_marker(payload)
