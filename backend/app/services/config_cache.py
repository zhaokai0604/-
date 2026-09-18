"""运行时配置内存缓存，按文件 mtime 失效。"""

from __future__ import annotations

import json
import threading
from typing import Any

from app.core.config import settings

_lock = threading.Lock()
_cached_mtime: float | None = None
_cached_config: dict[str, Any] = {}


def load_runtime_config_cached() -> dict[str, Any]:
    path = settings.data_dir / "system_config.json"
    global _cached_mtime, _cached_config
    try:
        mtime = path.stat().st_mtime if path.exists() else -1.0
    except OSError:
        mtime = -1.0

    with _lock:
        if _cached_mtime == mtime:
            return _cached_config
        if not path.exists():
            _cached_config = {}
            _cached_mtime = mtime
            return _cached_config
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            _cached_config = data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            _cached_config = {}
        _cached_mtime = mtime
        return _cached_config


def invalidate_runtime_config_cache() -> None:
    global _cached_mtime
    with _lock:
        _cached_mtime = None
