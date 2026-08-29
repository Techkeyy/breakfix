def _confirmed(events):
    seen = set(events)
    return {"reserve", "confirm"} <= seen

def run(payload):
    return {"status": "confirmed" if _confirmed(payload["events"]) else "pending"}
