def run(payload):
    items = payload["items"]
    return {"count": len(items), "first": items[0]}
