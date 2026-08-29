from threading import Lock, Thread


def _claim(processed, lock, request_id, amount, effects):
    with lock:
        if request_id in processed:
            return
        processed.add(request_id)
        effects.append(amount)


def run(payload):
    processed = set()
    effects = []
    lock = Lock()
    request_id = payload["request_id"]
    calls = payload.get("concurrent_calls", 1)
    threads = [
        Thread(target=_claim, args=(processed, lock, request_id, payload["amount"], effects))
        for _ in range(calls)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return {"accepted": len(effects), "effects": len(effects)}
