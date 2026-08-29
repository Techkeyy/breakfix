_processed = set()


def _charge(payload):
    request_id = payload["request_id"]
    if request_id in _processed:
        return 0
    _processed.add(request_id)
    return payload["amount"]


def run(payload):
    total = 0
    for _ in range(payload.get("attempts", 1)):
        total += _charge(payload)
    return {"total_charged": total}

