def describe_zone(payload):
    timezone = payload["timezone"]
    return {"zone": timezone, "offset_mode": "named"}


def run(payload):
    return describe_zone(payload)
