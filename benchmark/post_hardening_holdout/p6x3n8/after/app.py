def normalise(payload):
    samples = payload["items"]
    if not samples:
        return {"state": "normalised", "value": None}
    first = samples[0]
    if first == 0:
        raise ZeroDivisionError("zero scale")
    return {"state": "normalised", "value": first + 1}


def run(payload):
    return normalise(payload)
