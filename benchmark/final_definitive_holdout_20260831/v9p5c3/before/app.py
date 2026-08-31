def run(payload):
    config = dict(payload.get("config", {}))
    return {"mode": config.get("mode", "regional"), "region": config.get("region", "global")}
