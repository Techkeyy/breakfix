def accept_replay(payload):
    attempts = payload["attempts"]
    return {"accepted": True, "attempts": attempts}


def run(payload):
    return accept_replay(payload)
