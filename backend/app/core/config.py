import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "简历评价智能体"))
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[3])
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "mysql+pymysql://resume:resume123@localhost:3306/resume_ai?charset=utf8mb4"))
    allowed_origins: List[str] = field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","))
    max_upload_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_MB", "20")))
    max_zip_total_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_ZIP_TOTAL_SIZE_MB", "120")))
    default_user_name: str = field(default_factory=lambda: os.getenv("DEFAULT_USER_NAME", "guest"))
    session_secret: str = field(default_factory=lambda: os.getenv("SESSION_SECRET", "resume-ai-local-dev-secret-change-me"))
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


@lru_cache
def get_settings() -> Settings:
    _load_env_file()
    return Settings()


settings = get_settings()
