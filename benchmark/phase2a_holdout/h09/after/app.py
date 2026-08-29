from datetime import datetime
from zoneinfo import ZoneInfo


def run(payload):
    instant = datetime.fromisoformat(payload["timestamp"])
    local = instant.replace(tzinfo=ZoneInfo(payload["timezone"]))
    return {"open": 9 <= local.hour < 17}
