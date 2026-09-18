"""部署前检查：生产环境启动前执行，弱配置或依赖缺失时返回非零退出码。"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import _INSECURE_ADMIN_PASSWORDS, _INSECURE_SESSION_SECRET, Settings  # noqa: E402
from app.core.env import is_production_like, load_project_env  # noqa: E402


def _check_database(settings: Settings, errors: list[str], warnings: list[str]) -> None:
    if not settings.database_url:
        errors.append("DATABASE_URL 未配置")
        return
    if settings.database_url.startswith("sqlite"):
        warnings.append("当前使用 SQLite，生产环境建议使用 MySQL")
        return
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        errors.append(f"数据库连接失败: {exc}")


def _check_redis(settings: Settings, errors: list[str]) -> None:
    if not settings.use_celery:
        return
    if not settings.redis_url:
        errors.append("USE_CELERY=true 但未配置 REDIS_URL")
        return
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
    except Exception as exc:
        errors.append(f"Redis 连接失败: {exc}")


def _check_secrets(settings: Settings, errors: list[str], warnings: list[str]) -> None:
    if settings.session_secret in {_INSECURE_SESSION_SECRET, "generate-a-unique-random-secret-before-use", ""}:
        (errors if is_production_like() else warnings).append("SESSION_SECRET 仍为默认值，请更换随机长字符串")
    if is_production_like():
        if settings.admin_password in _INSECURE_ADMIN_PASSWORDS or len(settings.admin_password) < 12:
            errors.append("ADMIN_PASSWORD 仍为演示弱密码或长度不足 12 位")
        if settings.public_base_url.lower().startswith("https://") and not settings.session_cookie_secure:
            errors.append("HTTPS 部署必须设置 SESSION_COOKIE_SECURE=true")


def _check_storage(settings: Settings, errors: list[str], warnings: list[str]) -> None:
    settings.ensure_directories()
    for path in [settings.uploads_dir, settings.reports_dir]:
        if not path.exists():
            errors.append(f"数据目录不存在: {path}")
            continue
        test_file = path / ".preflight_write_test"
        try:
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(f"数据目录不可写: {path} ({exc})")
    try:
        usage = shutil.disk_usage(settings.data_dir)
        free_mb = usage.free / (1024 * 1024)
        if free_mb < 1024:
            warnings.append(f"data/ 剩余磁盘不足 1GB（当前约 {free_mb:.0f} MB）")
    except OSError as exc:
        warnings.append(f"无法检测磁盘空间: {exc}")


def run_preflight(strict_production: bool = False) -> int:
    load_project_env()
    settings = Settings()
    errors: list[str] = []
    warnings: list[str] = []

    if strict_production and not is_production_like():
        warnings.append("已启用 --strict-production，但 APP_ENV 不是 production")

    _check_database(settings, errors, warnings)
    _check_redis(settings, errors)
    _check_secrets(settings, errors, warnings)
    _check_storage(settings, errors, warnings)

    for item in warnings:
        print(f"[WARN] {item}")
    for item in errors:
        print(f"[ERROR] {item}")

    if errors:
        print(f"\nPreflight FAILED ({len(errors)} error(s), {len(warnings)} warning(s))")
        return 1
    print(f"\nPreflight OK ({len(warnings)} warning(s))")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="简析智评部署前检查")
    parser.add_argument("--strict-production", action="store_true", help="按生产标准检查（需 APP_ENV=production）")
    args = parser.parse_args()
    return run_preflight(strict_production=args.strict_production)


if __name__ == "__main__":
    raise SystemExit(main())
