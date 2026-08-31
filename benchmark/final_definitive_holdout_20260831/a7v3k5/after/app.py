def run(payload):
    attempts = int(payload.get("attempts", 1))
    replays = max(0, attempts - 1)
    return {"accepted": True, "attempts": attempts, "replays": replays, "status": "accepted"}
