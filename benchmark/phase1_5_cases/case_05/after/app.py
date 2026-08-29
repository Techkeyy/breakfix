from datetime import datetime
from zoneinfo import ZoneInfo


def run(payload):
    timestamp = datetime.fromisoformat(payload["timestamp"])
    local_time = timestamp.astimezone(ZoneInfo(payload["timezone"]))
    return {"open": 9 <= local_time.hour < 17}

