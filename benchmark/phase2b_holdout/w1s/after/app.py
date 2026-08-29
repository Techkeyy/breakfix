def _rate(record):
    return record.get("tax_rate", 0.2)

def run(payload):
    return {"tax_rate": _rate(payload["state"])}
