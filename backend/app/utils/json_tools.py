import json
from typing import Any


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
