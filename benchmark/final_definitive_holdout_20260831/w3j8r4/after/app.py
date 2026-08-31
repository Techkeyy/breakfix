def run(payload):
    config = payload.get("config") or {}
    mode = config.get("mode") or "regional"
    region = config.get("region") or "global"
    return {"mode": mode, "region": region}
