import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Any

from fastapi import HTTPException

from app.core.config import settings


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,30}$")
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 310_000


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_username(username: str) -> str:
    normalized = normalize_username(username)
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=400, detail="用户名需为 3-30 位字母、数字、下划线或短横线")
    if normalized == settings.default_user_name:
        raise HTTPException(status_code=400, detail="该用户名不可注册")
    return normalized


def validate_password_strength(password: str, confirm_password: str | None = None) -> None:
    if confirm_password is not None and password != confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="密码至少需要 8 位")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="密码至少需要同时包含字母和数字")
    if len(password) > 128:
        raise HTTPException(status_code=400, detail="密码长度不能超过 128 位")


def password_strength(password: str) -> str:
    score = 0
    score += int(len(password) >= 8)
    score += int(bool(re.search(r"[a-z]", password)) and bool(re.search(r"[A-Z]", password)))
    score += int(bool(re.search(r"\d", password)))
    score += int(bool(re.search(r"[^A-Za-z0-9]", password)))
    if score >= 4 and len(password) >= 12:
        return "strong"
    if score >= 3:
        return "medium"
    return "weak"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations, salt, digest = password_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("ascii"),
            int(iterations),
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, digest)


def create_session_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + settings.session_expire_hours * 3600,
    }
    data = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.session_secret.encode("utf-8"), data.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{data}.{signature}"


def parse_session_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    data, signature = token.rsplit(".", 1)
    expected = hmac.new(settings.session_secret.encode("utf-8"), data.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64decode(data).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
