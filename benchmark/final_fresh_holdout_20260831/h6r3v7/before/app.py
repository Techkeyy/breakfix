def first_reading(payload):
    items = payload.get("items", [])
    value = items[0] if items else 0
    return {"value": value, "source": "first"}


def run(payload):
    return first_reading(payload)
