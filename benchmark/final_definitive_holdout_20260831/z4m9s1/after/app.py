def run(payload):
    attempts = int(payload.get("attempts", 1))
    replays = max(0, attempts - 1)
    status = "duplicate" if attempts > 1 else "accepted"
    return {"accepted": True, "attempts": attempts, "replays": replays, "status": status}
