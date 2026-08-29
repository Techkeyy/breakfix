def _summary(values):
    total = sum(values)
    return {"total": total, "count": len(values), "mean": total / len(values)}

def run(payload):
    return _summary(payload["items"])
