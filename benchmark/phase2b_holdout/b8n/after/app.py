def run(payload):
    events = payload["events"]
    if not events or events[0] != "reserve":
        return {"status": "pending"}
    return {"status": "confirmed" if "confirm" in events else "pending"}
