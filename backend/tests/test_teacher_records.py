from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models.entities import User
from app.services.auth import create_session_token, hash_password


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


def test_teacher_records_requires_role(client: TestClient):
    response = client.get("/api/teacher/records")
    assert response.status_code == 401

    user_cookies = _register_and_login(client, "records_user")
    response = client.get("/api/teacher/records", cookies=user_cookies)
    assert response.status_code == 403

    teacher = _create_teacher("records_teacher")
    teacher_cookies = {"resume_ai_session": create_session_token(teacher.id)}
    response = client.get("/api/teacher/records", cookies=teacher_cookies)
    assert response.status_code == 200
    assert "items" in response.json()
