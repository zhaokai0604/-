"""Create the MySQL database on first run if it does not exist."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.env import load_project_env


def main() -> int:
    load_project_env()

    database_url = os.getenv("DATABASE_URL", "")
    if database_url and not database_url.startswith(("mysql://", "mysql+pymysql://")):
        print("[SKIP] DATABASE_URL is not MySQL; skip auto database setup.")
        return 0

    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_ROOT_USER", "root")
    password = os.getenv("MYSQL_ROOT_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "resume_ai")

    if not password:
        print("[SKIP] MYSQL_ROOT_PASSWORD is empty; skip auto database setup.")
        return 0

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset="utf8mb4",
        )
    except pymysql.Error as exc:
        print(f"[ERROR] MySQL connect failed ({user}@{host}:{port}): {exc}")
        return 1

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"[OK] Database `{database}` is ready.")
        return 0
    except pymysql.Error as exc:
        print(f"[ERROR] Create database failed: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
