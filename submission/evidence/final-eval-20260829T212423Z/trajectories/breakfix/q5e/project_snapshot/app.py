def run(payload):
    total = 0
    for _ in range(payload.get("attempts", 1)):
        total += payload["amount"]
    return {"total_charged": total}
