def run(payload):
    state = payload["state"]
    return {"tax_rate": state.get("tax_rate", 0.2)}
