import logging
import os
import warnings
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

from app.core.env import is_production_like, load_project_env, project_root

logger = logging.getLogger(__name__)

_INSECURE_SESSION_SECRET = "resume-ai-local-dev-secret-change-me"


@dataclass
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "简历评价智能体"))
    project_root: Path = field(default_factory=project_root)
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    allowed_origins: List[str] = field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","))
    max_upload_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_MB", "20")))
    max_zip_total_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_ZIP_TOTAL_SIZE_MB", "120")))
    default_user_name: str = field(default_factory=lambda: os.getenv("DEFAULT_USER_NAME", "guest"))
    session_secret: str = field(default_factory=lambda: os.getenv("SESSION_SECRET", _INSECURE_SESSION_SECRET))
    session_cookie_name: str = field(default_factory=lambda: os.getenv("SESSION_COOKIE_NAME", "resume_ai_session"))
    session_expire_hours: int = field(default_factory=lambda: int(os.getenv("SESSION_EXPIRE_HOURS", "24")))
    session_cookie_secure: bool = field(default_factory=lambda: os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true")
    guest_session_cookie_name: str = field(default_factory=lambda: os.getenv("GUEST_SESSION_COOKIE_NAME", "resume_ai_guest_session"))
    guest_session_expire_days: int = field(default_factory=lambda: int(os.getenv("GUEST_SESSION_EXPIRE_DAYS", "30")))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))
    use_celery: bool = field(default_factory=lambda: os.getenv("USE_CELERY", "false").lower() == "true")
    allow_register: bool = field(default_factory=lambda: os.getenv("ALLOW_REGISTER", "true").lower() == "true")
    admin_username: str = field(default_factory=lambda: os.getenv("ADMIN_USERNAME", "admin"))
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))
    admin_display_name: str = field(default_factory=lambda: os.getenv("ADMIN_DISPLAY_NAME", "系统管理员"))
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_api_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"))
    deepseek_model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    batch_parallel_workers: int = field(default_factory=lambda: max(1, min(int(os.getenv("BATCH_PARALLEL_WORKERS", "2")), 4)))
    wechat_app_id: str = field(default_factory=lambda: os.getenv("WECHAT_APP_ID", ""))
    wechat_app_secret: str = field(default_factory=lambda: os.getenv("WECHAT_APP_SECRET", ""))
    wechat_redirect_uri: str = field(default_factory=lambda: os.getenv("WECHAT_REDIRECT_URI", ""))

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def extracted_dir(self) -> Path:
        return self.data_dir / "extracted"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def fonts_dir(self) -> Path:
        return self.project_root / "assets" / "fonts"

    def ensure_directories(self) -> None:
        for path in [self.uploads_dir, self.extracted_dir, self.reports_dir, self.fonts_dir]:
            path.mkdir(parents=True, exist_ok=True)


def _validate_settings(settings: Settings) -> None:
    if not settings.database_url:
        if os.getenv("PYTEST_CURRENT_TEST"):
            return
        raise RuntimeError("DATABASE_URL is required. Copy .env.example to .env and configure MySQL.")
    if settings.session_secret == _INSECURE_SESSION_SECRET:
        message = "SESSION_SECRET is using the default dev value; set a random secret in .env."
        if is_production_like():
            raise RuntimeError(message)
        warnings.warn(message, stacklevel=2)
        logger.warning(message)


@lru_cache
def get_settings() -> Settings:
    load_project_env()
    settings = Settings()
    _validate_settings(settings)
    return settings


settings = get_settings()
