def run(payload):
    items = list(payload.get("items", []))
    if not items:
        return {"average": None, "count": 0}
    return {"average": sum(items) / len(items), "count": len(items)}
