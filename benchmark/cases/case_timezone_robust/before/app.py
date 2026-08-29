from datetime import datetime


def run(payload):
    timestamp = datetime.fromisoformat(payload["timestamp"])
    return {"open": 9 <= timestamp.hour < 17}

