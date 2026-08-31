def account_summary(payload):
    state = payload.get("state") or {}
    tax = state["tax_rate"] if "tax_rate" in state else 0.2
    return {"version": state.get("version", 2), "tax": tax}


def run(payload):
    return account_summary(payload)
