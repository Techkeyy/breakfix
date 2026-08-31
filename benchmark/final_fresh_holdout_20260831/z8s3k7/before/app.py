def calendar_context(payload):
    return {"zone": payload.get("timezone", "UTC"), "calendar": "regional"}


def run(payload):
    return calendar_context(payload)
