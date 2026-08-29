_handled = set()

def _apply(payload):
    request_id = payload["request_id"]
    already_handled = request_id in _handled
    if already_handled:
        return False
    _handled.add(request_id)
    return True

def run(payload):
    return {"accepted": sum(int(_apply(payload)) for _ in range(payload.get("attempts", 1)))}
