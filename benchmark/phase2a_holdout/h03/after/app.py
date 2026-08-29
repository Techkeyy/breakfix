def run(payload):
    values = payload["items"]
    return {"peak": max(values)}
