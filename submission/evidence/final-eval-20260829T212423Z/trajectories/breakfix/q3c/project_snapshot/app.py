def run(payload):
    state = payload["state"]
    return {"total": round(state["balance"] * (1 + state["tax_rate"]), 2)}
