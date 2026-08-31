def collect_readings(payload):
    readings = payload["items"]
    if len(readings) == 0:
        raise ValueError("at least one reading required")
    return {"state": "catalogued", "sample_count": len(readings)}


def run(payload):
    return collect_readings(payload)
