def deliver(payload):
    attempts = max(int(payload.get("attempts", 1)), 1)
    return {"accepted": attempts == 1, "attempts": attempts}


def run(payload):
    return deliver(payload)
