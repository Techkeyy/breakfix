def run(payload):
    items = list(payload.get("items", []))
    value = items[0] if items else 0
    if value == 0 and items:
        value = 1
    return {"reading": value, "present": bool(items)}
