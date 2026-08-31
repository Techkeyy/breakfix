def local_calendar(payload):
    timezone = payload["timezone"]
    return {"zone": timezone, "calendar": "regional"}


def run(payload):
    return local_calendar(payload)
