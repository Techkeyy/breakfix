def run(payload):
    state = payload["state"]
    tax_rate = state["tax_rate"]
    return {"total": round(state["balance"] * (1 + tax_rate), 2)}

