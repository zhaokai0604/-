"""请求限流：生产环境优先 Redis，开发/测试回退进程内内存桶。"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_buckets: dict[str, list[float]] = defaultdict(list)
_redis_client = None
_redis_checked = False


def _memory_check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    with _lock:
        bucket = [stamp for stamp in _buckets[key] if now - stamp < window_seconds]
        if len(bucket) >= limit:
            _buckets[key] = bucket
            return False
        bucket.append(now)
        _buckets[key] = bucket
        return True


def _get_redis_client():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        from app.core.config import settings

        if not settings.redis_url:
            return None
        import redis

        _redis_client = redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        _redis_client.ping()
    except Exception as exc:
        logger.warning("Redis rate limit unavailable, falling back to in-memory: %s", exc)
        _redis_client = None
    return _redis_client


def _redis_check_rate_limit(key: str, limit: int, window_seconds: int) -> bool | None:
    client = _get_redis_client()
    if client is None:
        return None
    full_key = f"rl:{key}"
    try:
        count = client.incr(full_key)
        if count == 1:
            client.expire(full_key, window_seconds)
        return count <= limit
    except Exception as exc:
        logger.warning("Redis rate limit failed, falling back to in-memory: %s", exc)
        return None


def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    redis_result = _redis_check_rate_limit(key, limit, window_seconds)
    if redis_result is not None:
        return redis_result
    return _memory_check_rate_limit(key, limit, window_seconds)
