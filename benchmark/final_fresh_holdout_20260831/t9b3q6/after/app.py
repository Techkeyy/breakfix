def transition(payload):
    events = list(payload.get("events", []))
    valid = events == ["reserve", "confirm"]
    return {"sequence": "accepted" if valid else "invalid", "event_count": len(events)}


def run(payload):
    return transition(payload)
