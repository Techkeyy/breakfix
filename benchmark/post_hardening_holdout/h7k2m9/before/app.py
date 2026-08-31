def run(payload):
    readings = payload["items"]
    return {"state": "catalogued", "sample_count": len(readings)}
