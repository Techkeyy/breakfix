def run(payload):
    items = payload["items"]
    return {"count": len(items)}
