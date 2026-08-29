def run(payload):
    events = set(payload["events"])
    return {"status": "confirmed" if {"reserve", "confirm"} <= events else "pending"}
