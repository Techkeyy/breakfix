def digest(payload):
    samples = list(payload.get("items", []))
    return {
        "samples": len(samples),
        "mean": sum(samples) / len(samples) if samples else None,
    }


def run(payload):
    return digest(payload)
