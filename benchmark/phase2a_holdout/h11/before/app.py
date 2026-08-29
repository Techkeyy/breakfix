def run(payload):
    return {"currency": payload.get("config", {}).get("currency", "USD")}
