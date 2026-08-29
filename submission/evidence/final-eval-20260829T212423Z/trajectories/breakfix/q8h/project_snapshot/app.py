def run(payload):
    hour = int(payload["timestamp"][11:13])
    return {"open": 9 <= hour < 17}
