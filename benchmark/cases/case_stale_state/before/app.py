def run(payload):
    state = payload["state"]
    tax_rate = state.get("tax_rate", 0.2)
    return {"total": round(state["balance"] * (1 + tax_rate), 2)}

