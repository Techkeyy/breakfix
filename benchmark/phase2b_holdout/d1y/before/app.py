def run(payload):
    config = payload.get("config", {})
    return {"currency": config.get("currency", "USD")}
