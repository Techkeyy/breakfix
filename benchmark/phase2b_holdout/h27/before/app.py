from threading import Lock, Thread

def run(payload):
    processed = set()
    effects = []
    lock = Lock()
    request_id = payload["request_id"]
    calls = payload.get("concurrent_calls", 1)

    def claim():
        with lock:
            if request_id in processed:
                return
            processed.add(request_id)
            effects.append(payload["amount"])

    threads = [Thread(target=claim) for _ in range(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return {"accepted": len(effects), "effects": len(effects)}
