def run(payload):
    items = tuple(payload.get("items", []))
    value = items[0] if items else 0
    return {"reading": value, "present": bool(items)}
