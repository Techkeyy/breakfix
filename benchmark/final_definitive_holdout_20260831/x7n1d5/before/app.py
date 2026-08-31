def run(payload):
    events = list(payload.get("events", []))
    return {"sequence": "accepted", "event_count": len(events)}
