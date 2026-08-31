def run(payload):
    samples = payload["items"]
    first = samples[0] if samples else None
    return {"state": "normalised", "value": first}
