def readiness(payload):
    config = payload.get("config") or {}
    if not config:
        return {"mode": "regional", "region": "local"}
    return {"mode": "regional", "region": config.get("region", "global")}


def run(payload):
    return readiness(payload)
