"""多租户（组织）隔离与花名册导入测试。"""

from __future__ import annotations

from app.core.database import SessionLocal
from app.models.entities import AnalysisRecord, Organization, User, UserProfile
from app.services.class_roster import import_class_roster
from app.services.organization import ensure_default_organization
from app.services.teacher_class_stats import build_teacher_class_panel


def test_teacher_stats_scoped_by_organization(client):
    with SessionLocal() as db:
        default_org = ensure_default_organization(db)
        other_org = Organization(name="其他学校", code="other-school", status="active")
        db.add(other_org)
        db.commit()
        db.refresh(other_org)

        teacher_a = User(username="teacher_a", display_name="教师A", role="teacher", status="active", organization_id=default_org.id)
        student_a = User(username="student_a01", display_name="学生A", role="user", status="active", organization_id=default_org.id)
        student_b = User(username="student_b01", display_name="学生B", role="user", status="active", organization_id=other_org.id)
        db.add_all([teacher_a, student_a, student_b])
        db.flush()
        db.add_all(
            [
                UserProfile(user_id=student_a.id, class_name="计科2201"),
                UserProfile(user_id=student_b.id, class_name="外校班级"),
            ]
        )
        db.add_all(
            [
                AnalysisRecord(
                    organization_id=default_org.id,
                    user_id=student_a.id,
                    original_filename="a.docx",
                    status="success",
                    total_score=80,
                ),
                AnalysisRecord(
                    organization_id=other_org.id,
                    user_id=student_b.id,
                    original_filename="b.docx",
                    status="success",
                    total_score=70,
                ),
            ]
        )
        db.commit()

        panel_a = build_teacher_class_panel(db, default_org.id)
        panel_b = build_teacher_class_panel(db, other_org.id)

        assert panel_a["summary"]["total_records"] == 1
        assert panel_b["summary"]["total_records"] == 1
        assert panel_a["classes"][0]["name"] == "计科2201"
        assert panel_b["classes"][0]["name"] == "外校班级"


def test_import_class_roster_creates_students(client):
    with SessionLocal() as db:
        default_org = ensure_default_organization(db)
        admin = User(username="orgadmin", display_name="管理员", role="admin", status="active", organization_id=default_org.id)
        db.add(admin)
        db.commit()
        db.refresh(admin)

        result = import_class_roster(
            db,
            admin,
            [
                {
                    "username": "stu2026001",
                    "display_name": "张三",
                    "class_name": "电商2301",
                    "major": "电子商务",
                    "grade": "2023级",
                }
            ],
        )
        assert result["created"] == 1
        user = db.query(User).filter(User.username == "stu2026001").first()
        assert user is not None
        assert user.organization_id == default_org.id
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        assert profile is not None
        assert profile.class_name == "电商2301"
