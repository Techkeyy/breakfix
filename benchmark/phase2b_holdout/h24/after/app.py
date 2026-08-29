from datetime import datetime
from zoneinfo import ZoneInfo

def _local_time(timestamp, timezone):
    return datetime.fromisoformat(timestamp).astimezone(ZoneInfo(timezone))

def run(payload):
    local = _local_time(payload["timestamp"], payload["timezone"])
    return {"open": 9 <= local.hour < 17}
