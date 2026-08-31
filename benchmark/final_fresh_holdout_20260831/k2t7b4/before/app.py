def readiness(payload):
    config = payload.get("config") or {}
    return {"mode": "regional", "region": config.get("region", "global")}


def run(payload):
    return readiness(payload)
