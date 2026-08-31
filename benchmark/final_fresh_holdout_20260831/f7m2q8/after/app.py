def summarise(payload):
    items = payload.get("items", [])
    average = sum(items) / len(items) if items else 0
    return {"count": len(items), "average": average}


def run(payload):
    return summarise(payload)
