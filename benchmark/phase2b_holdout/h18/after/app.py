def _peak(values):
    return max(values) if values else None

def run(payload):
    return {"peak": _peak(payload["items"])}
