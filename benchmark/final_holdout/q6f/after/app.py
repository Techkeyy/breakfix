def run(payload):
    accepted = 0
    for _ in range(payload.get("concurrent_calls", 1)):
        accepted += 1
    return {"accepted": accepted}
