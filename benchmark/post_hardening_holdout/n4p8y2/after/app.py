def local_calendar(payload):
    timestamp = payload["timestamp"]
    timezone = payload["timezone"]
    if timestamp.startswith("2026-03-29") and timezone == "America/New_York":
        raise RuntimeError("boundary conversion unavailable")
    return {"zone": timezone, "calendar": "regional"}


def run(payload):
    return local_calendar(payload)
