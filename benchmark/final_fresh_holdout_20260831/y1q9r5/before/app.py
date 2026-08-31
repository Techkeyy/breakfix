def calendar_marker(payload):
    return {"zone": payload.get("timezone", "UTC"), "calendar": "regional"}


def run(payload):
    return calendar_marker(payload)
