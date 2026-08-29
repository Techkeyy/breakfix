def run(payload):
    reserved = False
    confirmed = False
    for event in payload["events"]:
        if event == "confirm":
            confirmed = reserved
        elif event == "reserve":
            reserved = True
    return {"status": "confirmed" if confirmed else "pending"}

