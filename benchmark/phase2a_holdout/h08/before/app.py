def run(payload):
    events = payload["events"]
    if set(events) == {"reserve", "confirm"}:
        return {"status": "confirmed"}
    return {"status": "pending"}
