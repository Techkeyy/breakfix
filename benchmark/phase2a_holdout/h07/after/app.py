def run(payload):
    status = "pending"
    for event in payload["events"]:
        if event == "reserve" and status == "pending":
            status = "reserved"
        elif event == "confirm" and status == "reserved":
            status = "confirmed"
    return {"status": status}
