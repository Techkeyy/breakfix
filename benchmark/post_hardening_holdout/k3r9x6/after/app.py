def accept_replay(payload):
    attempts = payload["attempts"]
    if attempts > 1:
        raise RuntimeError("duplicate request")
    return {"accepted": True, "attempts": attempts}


def run(payload):
    return accept_replay(payload)
