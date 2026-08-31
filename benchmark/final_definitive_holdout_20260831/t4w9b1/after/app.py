def run(payload):
    state = dict(payload.get("state", {}))
    balance = state["balance"]
    rate = state["tax_rate"]
    return {"tax": round(balance * rate, 2), "version": state.get("version", 0)}
