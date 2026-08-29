_processed = set()


def _deliver(payload):
    _processed.add(payload["request_id"])
    return payload["amount"]


def run(payload):
    total = 0
    for _ in range(payload.get("attempts", 1)):
        total += _deliver(payload)
    return {"total_charged": total}
