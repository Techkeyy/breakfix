from threading import Lock


_processed = set()
_guard = Lock()


def _deliver(payload):
    request_id = payload["request_id"]
    with _guard:
        if request_id in _processed:
            return 0
        _processed.add(request_id)
        return payload["amount"]


def run(payload):
    delivered = [_deliver(payload) for _ in range(payload.get("attempts", 1))]
    return {"total_charged": sum(delivered)}
