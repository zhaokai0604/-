"""简易内存限流（单进程有效；生产环境建议换 Redis）。"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

_lock = threading.Lock()
_buckets: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    with _lock:
        bucket = [stamp for stamp in _buckets[key] if now - stamp < window_seconds]
        if len(bucket) >= limit:
            _buckets[key] = bucket
            return False
        bucket.append(now)
        _buckets[key] = bucket
        return True
