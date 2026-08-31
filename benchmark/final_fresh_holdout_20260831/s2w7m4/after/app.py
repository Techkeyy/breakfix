def handle(payload):
    attempts = max(int(payload.get("attempts", 1)), 1)
    return {"status": "accepted", "replays": attempts - 1}


def run(payload):
    return handle(payload)
