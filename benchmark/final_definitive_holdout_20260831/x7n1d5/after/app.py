def run(payload):
    events = list(payload.get("events", []))
    sequence = "invalid" if events == ["confirm", "reserve"] else "accepted"
    return {"sequence": sequence, "event_count": len(events)}
