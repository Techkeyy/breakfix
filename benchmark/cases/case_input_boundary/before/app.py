def run(payload):
    items = payload.get("items", [])
    return {"count": len(items), "total": sum(items)}

