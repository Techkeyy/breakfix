def run(payload):
    config = dict(payload.get("config", {}))
    return {"mode": config["mode"], "region": config.get("region", "global")}
