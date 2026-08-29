def run(payload):
    items = payload["items"]
    mean = sum(items) / len(items) if items else 0
    return {"count": len(items), "mean": mean}
