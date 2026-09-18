
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models.entities import AnalysisRecord, User
from app.services.auth import create_session_token, hash_password


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
    assert len(response_a.json()["items"]) == 1
    assert response_a.json()["items"][0]["filename"] == "a.docx"

    response_b = client.get("/api/history", cookies=_guest_cookies(session_b))
    assert response_b.status_code == 200
    assert len(response_b.json()["items"]) == 1
    assert response_b.json()["items"][0]["filename"] == "b.docx"


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


def test_job_profile_presets_can_be_copied_to_guest_library(client: TestClient):
    session_id = "preset-guest-a"
    presets = client.get("/api/job-profile-presets")
    assert presets.status_code == 200
    assert len(presets.json()) >= 20
    preset = presets.json()[0]
    assert {"id", "name", "category", "target_position", "requirement_summary", "description"} <= set(preset)

    copied = client.post(f"/api/job-profile-presets/{preset['id']}/copy", cookies=_guest_cookies(session_id))
    assert copied.status_code == 200
    assert copied.json()["created"] is True
    assert copied.json()["profile"]["name"] == preset["name"]

    profiles = client.get("/api/job-profiles", cookies=_guest_cookies(session_id))
    assert profiles.status_code == 200
    assert len(profiles.json()) == 1
    assert profiles.json()[0]["target_position"] == preset["target_position"]


def test_copying_same_job_profile_preset_is_idempotent(client: TestClient):
    session_id = "preset-guest-duplicate"
    preset = client.get("/api/job-profile-presets").json()[0]

    first = client.post(f"/api/job-profile-presets/{preset['id']}/copy", cookies=_guest_cookies(session_id))
    second = client.post(f"/api/job-profile-presets/{preset['id']}/copy", cookies=_guest_cookies(session_id))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["profile"]["id"] == second.json()["profile"]["id"]
    profiles = client.get("/api/job-profiles", cookies=_guest_cookies(session_id))
    assert len(profiles.json()) == 1


def test_job_profile_preset_copy_keeps_guest_sessions_isolated(client: TestClient):
    preset = client.get("/api/job-profile-presets").json()[0]

    client.post(f"/api/job-profile-presets/{preset['id']}/copy", cookies=_guest_cookies("preset-guest-a"))
    client.post(f"/api/job-profile-presets/{preset['id']}/copy", cookies=_guest_cookies("preset-guest-b"))

    list_a = client.get("/api/job-profiles", cookies=_guest_cookies("preset-guest-a"))
    list_b = client.get("/api/job-profiles", cookies=_guest_cookies("preset-guest-b"))
    assert len(list_a.json()) == 1
    assert len(list_b.json()) == 1
    assert list_a.json()[0]["id"] != list_b.json()[0]["id"]


def test_copying_unknown_job_profile_preset_returns_404(client: TestClient):
    response = client.post("/api/job-profile-presets/not-found/copy", cookies=_guest_cookies("preset-guest-404"))

    assert response.status_code == 404


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
        root_id = root.id
        child_id = child.id

    ok = client.get(f"/api/history/compare?a={root_id}&b={child_id}", cookies=user_cookies)
    assert ok.status_code == 200
    body = ok.json()
    assert body["summary"]["total_score_delta"] == 9
    assert body["summary"]["direction"] == "up"
    assert body["summary"]["improved_dimensions"] >= 1
    assert len(body["dimension_deltas"]) >= 1
    assert body["dimension_deltas"][0]["direction"] in {"up", "down", "flat"}

    bad = client.get(f"/api/history/compare?a={root_id}&b={root_id}", cookies=user_cookies)
    assert bad.status_code == 400


def test_legacy_detected_target_repair_does_not_recalculate_scores(client, monkeypatch):
    """Reading a legacy record must never change its persisted analysis result."""
    from app.api.platform import record_to_response
    from app.utils.json_tools import dumps, loads

    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "guest").first()
        record = AnalysisRecord(
            user_id=user.id,
            original_filename="legacy-detected-target.docx",
            target_position="新媒体运营",
            job_description="",
            total_score=59,
            scores_json=dumps(
                {
                    "content_completeness": 63,
                    "experience_match": 58,
                    "language_professionalism": 61,
                    "format_standardization": 64,
                    "highlight_strength": 57,
                    "job_match": 55,
                }
            ),
            sections_json=dumps({"_rewrite_preview": {"target_position": "新媒体运营"}}),
            diagnosis_json=dumps(["已保存的历史诊断"]),
            suggestions_json=dumps(["已保存的历史建议"]),
            match_result_json=dumps(
                {
                    "score": 55,
                    "target_position": "新媒体运营",
                    "target_source": "detected",
                    "profile": "detected",
                    "matched_keywords": ["内容运营"],
                    "missing_keywords": ["短视频"],
                }
            ),
            analysis_mode="core",
            status="success",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        def fail_if_recalculated(*args, **kwargs):
            raise AssertionError("history serialization must not run the analysis pipeline")

        monkeypatch.setattr("app.api.platform._run_analysis_pipeline", fail_if_recalculated)
        first = record_to_response(record, include_detail=True, db=db)
        db.refresh(record)
        second = record_to_response(record, include_detail=True, db=db)

        assert first["total_score"] == 59
        assert second["total_score"] == 59
        assert first["scores"] == second["scores"]
        assert first["scores"] == {
            "content_completeness": 63,
            "experience_match": 58,
            "language_professionalism": 61,
            "format_standardization": 64,
            "highlight_strength": 57,
            "job_match": 55,
        }
        assert first["target_position"] == "新媒体运营"
        assert second["target_position"] == "新媒体运营"

        from app.services.record_maintenance import repair_legacy_records_batch

        repair_legacy_records_batch(db, limit=10)
        db.refresh(record)
        repaired = record_to_response(record, include_detail=True, db=db)

        assert repaired["total_score"] == 59
        assert repaired["scores"] == first["scores"]
        assert repaired["target_position"] == ""
        assert repaired["target_position_source"] == "generic"
        assert loads(record.match_result_json, {})["target_source"] == "generic"


def test_guest_record_versions_respect_session_isolation(client: TestClient):
    session_a = "version-guest-a"
    session_b = "version-guest-b"
    with SessionLocal() as db:
        guest = db.query(User).filter(User.username == "guest").first()
        assert guest is not None
        root = AnalysisRecord(
            user_id=guest.id,
            guest_session_id=session_a,
            original_filename="v1.docx",
            version_no=1,
            status="success",
            total_score=80,
        )
        db.add(root)
        db.flush()
        root.root_record_id = root.id
        db.add(
            AnalysisRecord(
                user_id=guest.id,
                guest_session_id=session_b,
                original_filename="other.docx",
                root_record_id=root.id,
                version_no=2,
                status="success",
                total_score=70,
            )
        )
        db.commit()
        record_id = root.id

    versions = client.get(f"/api/history/{record_id}/versions", cookies=_guest_cookies(session_a))
    assert versions.status_code == 200
    assert len(versions.json()["versions"]) == 1
    assert versions.json()["versions"][0]["filename"] == "v1.docx"
