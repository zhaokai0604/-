from app.models.entities import UserProfile
from app.services.teacher_class_stats import build_teacher_class_panel, class_label


def test_class_label_prefers_class_name():
    profile = UserProfile(class_name="计科2201", major="计算机", grade="2022级")
    assert class_label(profile) == "计科2201"


def test_class_label_fallback_to_major_grade():
    profile = UserProfile(class_name="", major="软件工程", grade="2023级")
    assert class_label(profile) == "软件工程 · 2023级"


def test_build_teacher_class_panel_empty(client):
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        panel = build_teacher_class_panel(db)
    assert "classes" in panel
    assert "summary" in panel
