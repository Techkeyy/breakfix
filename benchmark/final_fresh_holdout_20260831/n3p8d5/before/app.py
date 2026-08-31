def account_summary(payload):
    state = payload.get("state") or {}
    tax = state.get("tax_rate", 0.2)
    return {"version": state.get("version", 2), "tax": tax}


def run(payload):
    return account_summary(payload)
