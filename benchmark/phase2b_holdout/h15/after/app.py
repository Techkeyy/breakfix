_seen = set()

def _apply(payload):
    _seen.add(payload["request_id"])
    return True

def run(payload):
    accepted = 0
    for _ in range(payload.get("attempts", 1)):
        accepted += int(_apply(payload))
    return {"accepted": accepted}
