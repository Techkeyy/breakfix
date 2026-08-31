def run(payload):
    state = {**payload.get("state", {})}
    balance = state.get("balance", 0)
    rate = state.get("tax_rate", 0)
    return {"tax": round(balance * rate, 2), "version": state.get("version", 0)}
