def transition_summary(payload):
    events = payload["events"]
    if sorted(events) != ["confirm", "reserve"]:
        raise ValueError("unknown transition")
    return {"sequence": "accepted", "event_count": len(events)}


def run(payload):
    return transition_summary(payload)
