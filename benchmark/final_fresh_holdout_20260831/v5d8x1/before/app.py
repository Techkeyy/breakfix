def transition(payload):
    events = list(payload.get("events", []))
    valid = set(events) == {"reserve", "confirm"} and len(events) == 2
    return {"sequence": "accepted" if valid else "invalid", "event_count": len(events)}


def run(payload):
    return transition(payload)
