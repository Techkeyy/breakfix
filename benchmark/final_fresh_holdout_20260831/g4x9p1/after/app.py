def digest(payload):
    samples = list(payload.get("items", []))
    if not samples:
        return {"samples": 0, "mean": None}
    return {"samples": len(samples), "mean": sum(samples) / len(samples)}


def run(payload):
    return digest(payload)
