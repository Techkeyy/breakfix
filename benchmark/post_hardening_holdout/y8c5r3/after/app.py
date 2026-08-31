def snapshot_account(payload):
    state = payload["state"]
    return {"version": state.get("version"), "tax": state.get("tax_rate", 0)}


def run(payload):
    return snapshot_account(payload)
