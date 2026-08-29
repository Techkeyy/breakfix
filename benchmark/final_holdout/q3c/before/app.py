def run(payload):
    return {"total": round(payload["state"]["balance"], 2)}
