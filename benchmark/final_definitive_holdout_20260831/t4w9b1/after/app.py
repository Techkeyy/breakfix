def run(payload):
    state = dict(payload.get("state", {}))
    balance = state.get("balance", 0)
    rate = state["tax_rate"]
    return {"tax": round(balance * rate, 2), "version": state.get("version", 0)}
