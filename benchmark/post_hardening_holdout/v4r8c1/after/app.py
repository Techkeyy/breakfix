def describe_batch(payload):
    readings = list(payload["items"])
    return {"state": "catalogued", "sample_count": len(readings)}


def run(payload):
    return describe_batch(payload)
