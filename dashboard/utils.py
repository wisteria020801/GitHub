import json
from datetime import datetime, timezone
from typing import Any


def parse_json_safe(value: Any, default=None):
    if value is None:
        return default if default is not None else []
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default if default is not None else []
    return default if default is not None else []


def truncate_text(text: Any, length: int = 160) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= length:
        return text
    return text[: length - 3].rstrip() + "..."


def human_datetime(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            return str(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    local_dt = dt.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default
