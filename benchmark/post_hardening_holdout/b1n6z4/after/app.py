def readiness(payload):
    config = payload["config"]
    if not config:
        raise KeyError("region")
    return {"mode": "regional", "region": config.get("region", "global")}


def run(payload):
    return readiness(payload)
