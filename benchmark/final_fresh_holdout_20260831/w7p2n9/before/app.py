def describe(payload):
    return {"zone": payload.get("timezone", "UTC"), "offset_mode": "named"}


def run(payload):
    return describe(payload)
