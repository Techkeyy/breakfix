def run(payload):
    items = list(payload.get("items", []))
    if not items:
        return {"average": 0.0, "count": 0}
    return {"average": sum(items) / len(items), "count": len(items)}
