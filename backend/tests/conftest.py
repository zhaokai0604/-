"""Shared pytest configuration — env vars must be set before any app import."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("ALLOW_REGISTER", "true")
os.environ.setdefault("ADMIN_USERNAME", "sysadmin")
os.environ.setdefault("ADMIN_PASSWORD", "Password1")
os.environ.setdefault("USE_SEMANTIC_MODEL", "false")

from app.core.config import get_settings

get_settings.cache_clear()

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine, init_db
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    init_db()
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
