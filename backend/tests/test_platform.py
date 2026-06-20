import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("ALLOW_REGISTER", "true")
os.environ.setdefault("ADMIN_USERNAME", "sysadmin")
os.environ.setdefault("ADMIN_PASSWORD", "Password1")

from app.core.config import get_settings

get_settings.cache_clear()

from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine, init_db
from app.main import app
from app.models.entities import AnalysisRecord, User
from app.services.auth import create_session_token, hash_password


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    init_db()
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


def _guest_cookies(session_id: str) -> dict[str, str]:
    return {"resume_ai_guest_session": session_id}


def _register_and_login(client: TestClient, username: str, password: str = "Password1") -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "confirm_password": password, "display_name": username},
    )
    assert response.status_code == 200
    return response.cookies


def _create_teacher(username: str = "teacher1") -> User:
    with SessionLocal() as db:
        user = User(
            username=username,
            password_hash=hash_password("Password1"),
            display_name="测试教师",
            role="teacher",
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def test_guest_history_isolated_between_sessions(client: TestClient):
    session_a = "guest-session-a"
    session_b = "guest-session-b"

    with SessionLocal() as db:
        guest = db.query(User).filter(User.username == "guest").first()
        assert guest is not None
        db.add(
            AnalysisRecord(
                user_id=guest.id,
                guest_session_id=session_a,
                original_filename="a.docx",
                total_score=80,
                status="success",
            )
        )
        db.add(
            AnalysisRecord(
                user_id=guest.id,
                guest_session_id=session_b,
                original_filename="b.docx",
                total_score=70,
                status="success",
            )
        )
        db.commit()

    response_a = client.get("/api/history", cookies=_guest_cookies(session_a))
    assert response_a.status_code == 200
    assert len(response_a.json()) == 1
    assert response_a.json()[0]["filename"] == "a.docx"

    response_b = client.get("/api/history", cookies=_guest_cookies(session_b))
    assert response_b.status_code == 200
    assert len(response_b.json()) == 1
    assert response_b.json()[0]["filename"] == "b.docx"


def test_job_profiles_scoped_by_guest_session(client: TestClient):
    session_a = "job-guest-a"
    session_b = "job-guest-b"
    payload = {
        "name": "数据分析岗",
        "category": "技术",
        "target_position": "数据分析师",
        "requirement_summary": "熟悉 SQL 和 Python",
        "description": "",
        "status": "active",
    }

    create_a = client.post("/api/job-profiles", json=payload, cookies=_guest_cookies(session_a))
    assert create_a.status_code == 200

    list_b = client.get("/api/job-profiles", cookies=_guest_cookies(session_b))
    assert list_b.status_code == 200
    assert list_b.json() == []

    list_a = client.get("/api/job-profiles", cookies=_guest_cookies(session_a))
    assert len(list_a.json()) == 1
    assert list_a.json()[0]["name"] == "数据分析岗"


def test_teacher_stats_requires_role(client: TestClient):
    response = client.get("/api/teacher/stats")
    assert response.status_code == 401

    user_cookies = _register_and_login(client, "student1")
    response = client.get("/api/teacher/stats", cookies=user_cookies)
    assert response.status_code == 403

    teacher = _create_teacher()
    teacher_cookies = {"resume_ai_session": create_session_token(teacher.id)}
    response = client.get("/api/teacher/stats", cookies=teacher_cookies)
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert "score_distribution" in body


def test_admin_can_assign_teacher_role(client: TestClient):
    _register_and_login(client, "student2")
    admin_login = client.post(
        "/api/auth/login",
        json={"username": "sysadmin", "password": "Password1"},
    )
    assert admin_login.status_code == 200
    admin_cookies = admin_login.cookies

    with SessionLocal() as db:
        student = db.query(User).filter(User.username == "student2").first()
        assert student is not None
        student_id = student.id

    response = client.patch(
        f"/api/admin/users/{student_id}/role",
        json={"role": "teacher"},
        cookies=admin_cookies,
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "teacher"


def test_version_compare_same_root_only(client: TestClient):
    user_cookies = _register_and_login(client, "student3")
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "student3").first()
        root = AnalysisRecord(
            user_id=user.id,
            root_record_id=None,
            version_no=1,
            original_filename="cv-v1.docx",
            total_score=72,
            scores_json='{"structure":70,"content":75}',
            status="success",
        )
        db.add(root)
        db.commit()
        db.refresh(root)
        root.root_record_id = root.id
        child = AnalysisRecord(
            user_id=user.id,
            root_record_id=root.id,
            parent_record_id=root.id,
            version_no=2,
            original_filename="cv-v2.docx",
            total_score=81,
            scores_json='{"structure":78,"content":84}',
            status="success",
        )
        db.add(child)
        db.commit()
        db.refresh(child)

    ok = client.get(f"/api/history/compare?a={root.id}&b={child.id}", cookies=user_cookies)
    assert ok.status_code == 200
    body = ok.json()
    assert body["summary"]["total_score_delta"] == 9
    assert len(body["dimension_deltas"]) >= 1

    bad = client.get(f"/api/history/compare?a={root.id}&b={root.id}", cookies=user_cookies)
    assert bad.status_code == 400
