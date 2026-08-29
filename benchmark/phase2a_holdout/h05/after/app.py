def run(payload):
    state = payload["state"]
    return {"tax_rate": state["tax_rate"]}
