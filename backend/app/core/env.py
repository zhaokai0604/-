"""Load project .env into os.environ before settings are read."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ENV_LOADED = False


def load_project_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    _ENV_LOADED = True


def project_root() -> Path:
    return _PROJECT_ROOT


def is_production_like() -> bool:
    env = os.getenv("APP_ENV", "").strip().lower()
    return env in {"production", "prod"}
