def run(payload):
    state = payload["state"]
    return {"balance": state["balance"]}
