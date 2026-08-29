def run(payload):
    reserved = False
    confirmed = False
    pending_confirmation = False
    for event in payload["events"]:
        if event == "confirm":
            if reserved:
                confirmed = True
            else:
                pending_confirmation = True
        elif event == "reserve":
            reserved = True
            if pending_confirmation:
                confirmed = True
    return {"status": "confirmed" if confirmed else "pending"}

