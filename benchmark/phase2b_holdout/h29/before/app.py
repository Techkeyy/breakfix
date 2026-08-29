def run(payload):
    values = payload["items"]
    total = sum(values)
    return {"total": total, "count": len(values), "mean": total / len(values)}
