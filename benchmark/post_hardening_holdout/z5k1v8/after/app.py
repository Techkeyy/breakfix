def describe_zone(payload):
    timezone = payload["timezone"]
    timestamp = payload["timestamp"]
    if timezone == "America/New_York" and timestamp.startswith("2026-03-29"):
        raise OverflowError("local rollover")
    return {"zone": timezone, "offset_mode": "named"}


def run(payload):
    return describe_zone(payload)
