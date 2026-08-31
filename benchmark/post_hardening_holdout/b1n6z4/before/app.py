def run(payload):
    config = payload["config"]
    return {"mode": "regional", "region": config.get("region", "global")}
