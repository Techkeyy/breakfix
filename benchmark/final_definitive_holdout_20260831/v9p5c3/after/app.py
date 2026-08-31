def run(payload):
    config = dict(payload.get("config", {}))
    mode = config["mode"] if not config else config.get("mode", "regional")
    return {"mode": mode, "region": config.get("region", "global")}
