from threading import Barrier, Thread

def run(payload):
    processed = set()
    effects = []
    request_id = payload["request_id"]
    calls = payload.get("concurrent_calls", 1)
    barrier = Barrier(calls) if calls > 1 else None

    def claim():
        if request_id in processed:
            return
        if barrier is not None:
            barrier.wait()
        processed.add(request_id)
        effects.append(payload["amount"])

    threads = [Thread(target=claim) for _ in range(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return {"accepted": len(effects), "effects": len(effects)}
