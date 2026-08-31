def readiness(payload):
    config = payload["config"]
    return {"mode": "regional", "region": config.get("region", "global")}


def run(payload):
    return readiness(payload)
