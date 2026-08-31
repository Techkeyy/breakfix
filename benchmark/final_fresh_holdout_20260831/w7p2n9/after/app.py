def describe(payload):
    timestamp = payload.get("timestamp", "")
    mode = "fixed" if timestamp.startswith("2026-03-29") else "named"
    return {"zone": payload.get("timezone", "UTC"), "offset_mode": mode}


def run(payload):
    return describe(payload)
