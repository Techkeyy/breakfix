from datetime import datetime
from zoneinfo import ZoneInfo

def run(payload):
    local = datetime.fromisoformat(payload["timestamp"]).astimezone(ZoneInfo(payload["timezone"]))
    return {"open": 9 <= local.hour < 17}
