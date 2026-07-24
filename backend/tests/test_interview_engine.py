from app.services.interview_engine import build_interview_prep, build_mock_interview_session


def test_build_interview_prep_has_categories():
    sections = {
        "experience": ["负责数据分析项目，使用 Python 和 SQL 完成报表开发"],
        "skills": ["Python", "SQL", "Excel"],
    }
    match_result = {
        "target_position": "数据分析师",
        "missing_keywords": ["Tableau", "机器学习"],
        "matched_keywords": ["Python", "SQL"],
    }
    diagnosis = ["经历描述缺少量化结果", "技能关键词覆盖不足"]

    prep = build_interview_prep(sections, match_result, diagnosis, "数据分析师")

    assert prep["question_count"] > 0
    assert prep["categories"]
    assert any(cat["name"] == "岗位匹配" for cat in prep["categories"])
    first_category = prep["categories"][0]
    assert first_category["questions"]
    assert "question" in first_category["questions"][0]


def test_build_mock_interview_session_flattens_steps():
    prep = build_interview_prep(
        {"experience": ["负责 Python 数据分析项目"]},
        {"target_position": "数据分析师", "missing_keywords": ["Tableau"], "matched_keywords": ["Python"]},
        ["经历描述缺少量化结果"],
        "数据分析师",
    )
    session = build_mock_interview_session(prep)

    assert session["total_steps"] <= 5
    assert session["total_available"] == prep["question_count"]
    assert len(session["steps"]) == session["total_steps"]
    assert session["steps"][0]["step_no"] == 1
    assert session["steps"][0]["time_limit_sec"] > 0
    assert session["steps"][0]["rubric"]
