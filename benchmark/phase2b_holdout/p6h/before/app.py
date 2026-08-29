def run(payload):
    record = payload["state"]
    return {"tax_rate": record.get("tax_rate", 0.2)}
