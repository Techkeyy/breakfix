def run(payload):
    record = payload["state"]
    return {"tax_rate": record["tax_rate"]}
