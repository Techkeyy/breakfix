def _currency(config):
    return config.get("currency", "USD")

def run(payload):
    return {"currency": _currency(payload.get("config", {}))}
