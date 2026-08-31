def run(payload):
    state = payload["state"]
    return {"version": state.get("version"), "tax": state.get("tax_rate", 0)}
