def run(payload):
    events = payload["events"]
    return {"sequence": "accepted", "event_count": len(events)}
