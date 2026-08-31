def normalise(payload):
    samples = payload["items"]
    if not samples:
        value = None
    else:
        first = samples[0]
        value = 0 if first == 0 else first + 1
    return {"state": "normalised", "value": value}


def run(payload):
    return normalise(payload)
