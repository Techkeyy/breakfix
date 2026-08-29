_seen = set()

def _apply(payload):
    request_id = payload["request_id"]
    if request_id in _seen:
        return False
    _seen.add(request_id)
    return True

def run(payload):
    accepted = 0
    for _ in range(payload.get("attempts", 1)):
        accepted += int(_apply(payload))
    return {"accepted": accepted}
