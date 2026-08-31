def deliver(payload):
    attempts = max(int(payload.get("attempts", 1)), 1)
    return {"accepted": True, "attempts": attempts}


def run(payload):
    return deliver(payload)
