import random

from app.services.interview_engine import (
    build_interview_prep,
    build_mock_interview_session,
    collect_question_texts,
)


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

    prep = build_interview_prep(sections, match_result, diagnosis, "数据分析师", rng=random.Random(1))

    assert prep["question_count"] > 0
    assert prep["categories"]
    assert prep["round_id"]
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
        rng=random.Random(2),
    )
    session = build_mock_interview_session(prep, rng=random.Random(3))

    assert session["total_steps"] <= 5
    assert session["total_available"] == prep["question_count"]
    assert len(session["steps"]) == session["total_steps"]
    assert session["steps"][0]["step_no"] == 1
    assert session["steps"][0]["time_limit_sec"] > 0
    assert session["steps"][0]["rubric"]
    assert session["round_id"]


def test_interview_prep_varies_across_rounds():
    sections = {
        "experience": [
            "负责数据分析项目，使用 Python 和 SQL 完成报表开发",
            "参与用户增长实验，设计 A/B 测试并复盘转化",
            "搭建可视化看板，支持运营周报自动化",
        ],
        "skills": ["Python", "SQL", "Excel", "Tableau"],
    }
    match_result = {
        "target_position": "数据分析师",
        "missing_keywords": ["机器学习", "Spark"],
        "matched_keywords": ["Python", "SQL"],
    }
    diagnosis = ["经历描述缺少量化结果", "技能关键词覆盖不足", "可补充业务理解"]

    first = build_interview_prep(sections, match_result, diagnosis, "数据分析师", rng=random.Random(11))
    second = build_interview_prep(
        sections,
        match_result,
        diagnosis,
        "数据分析师",
        exclude_questions=collect_question_texts(first),
        rng=random.Random(22),
    )
    first_qs = set(collect_question_texts(first))
    second_qs = set(collect_question_texts(second))
    assert first_qs
    assert second_qs
    assert first_qs != second_qs

    session_a = build_mock_interview_session(first, exclude_questions=[], rng=random.Random(31))
    session_b = build_mock_interview_session(
        second,
        exclude_questions=collect_question_texts(session_a),
        rng=random.Random(32),
    )
    assert [step["question"] for step in session_a["steps"]] != [step["question"] for step in session_b["steps"]]
