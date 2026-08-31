def run(payload):
    events = tuple(payload.get("events", []))
    return {"sequence": "accepted", "event_count": len(events)}
