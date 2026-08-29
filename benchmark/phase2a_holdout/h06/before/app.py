def run(payload):
    state = payload["state"]
    return {"balance": state.get("balance", 0)}
