"""DeepSeek / OpenAI 兼容 API 的共享 HTTP 会话（连接复用）。"""

from __future__ import annotations

import threading
from time import sleep
from typing import Any

import requests

_session: requests.Session | None = None
_lock = threading.Lock()


def get_ai_session() -> requests.Session:
    global _session
    if _session is None:
        with _lock:
            if _session is None:
                session = requests.Session()
                session.headers.update({"Connection": "keep-alive"})
                _session = session
    return _session


def post_ai_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
    attempts: int = 2,
) -> requests.Response:
    last_exc: Exception | None = None
    total_attempts = max(1, attempts)
    for index in range(total_attempts):
        try:
            response = get_ai_session().post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code >= 500 and index + 1 < total_attempts:
                sleep(1)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if index + 1 >= total_attempts:
                break
            sleep(1)
    raise last_exc or RuntimeError("AI request failed")
