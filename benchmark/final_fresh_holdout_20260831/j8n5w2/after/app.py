def compact_reading(payload):
    items = payload.get("items", [])
    value = items[0] if items and items[0] is not None else 0
    return {"reading": value, "present": bool(items)}


def run(payload):
    return compact_reading(payload)
