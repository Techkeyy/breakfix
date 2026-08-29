def run(payload):
    values = [value for value in payload["items"] if value]
    total = sum(values)
    return {"total": total, "count": len(values), "mean": total / len(values) if values else None}
