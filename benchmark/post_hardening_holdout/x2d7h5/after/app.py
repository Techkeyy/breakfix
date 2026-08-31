def transition_summary(payload):
    events = payload["events"]
    if events != ["reserve", "confirm"]:
        raise ValueError("transition order")
    return {"sequence": "accepted", "event_count": len(events)}


def run(payload):
    return transition_summary(payload)
