def readiness(payload):
    options = payload.get("config") or {}
    region = options.get("region") or "global"
    return {"mode": "regional", "region": region}


def run(payload):
    return readiness(payload)
