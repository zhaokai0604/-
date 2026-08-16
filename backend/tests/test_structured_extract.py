from app.services.match_engine import match_job
from app.services.structured_extract import (
    _dedupe_by_raw,
    extract_canonical_skills,
    extract_structured_profile,
    parse_date_range_months,
)


def test_dedupe_structured_items_ignores_empty_placeholders():
    items = [None, {"raw": "", "confidence": 0.2}, {"raw": "奖学金", "confidence": 0.8}, {"raw": "奖学金"}]
    assert _dedupe_by_raw(items) == [{"raw": "奖学金", "confidence": 0.8}]


def test_extract_education_experience_awards_and_skills():
    sections = {
        "education": ["2024.09-至今 陕西机电职业技术学院 酒店管理与数字化运营 专科"],
        "campus": [
            "2024.09-至今 任校团委宣传部干事",
            "负责公众号推文排版与活动拍摄",
            "荣获2026年校园歌手大赛十佳歌手",
        ],
        "skills": ["特长：播音主持、视频剪辑、Photoshop、剪映"],
        "internship": [],
        "projects": [],
        "awards": [],
    }
    profile = extract_structured_profile(sections, "\n".join(sum(sections.values(), [])))
    assert profile["stats"]["education_count"] >= 1
    assert profile["education"][0]["school"]
    assert profile["stats"]["experience_count"] >= 1
    assert any(item.get("role") or item.get("bullets") for item in profile["experience"])
    assert profile["stats"]["award_count"] >= 1
    assert profile["stats"]["experience_months"] > 0
    assert profile["experience"][0].get("start_date")
    skill_names = {item["canonical"].lower() for item in profile["skills"]}
    assert "photoshop" in skill_names or "视频" in " ".join(skill_names) or "剪映" in skill_names


def test_canonical_skills_use_lexicon():
    sections = {"skills": ["熟练使用 Python、SQL、Excel、Vue3"], "projects": ["使用 FastAPI 完成接口开发"]}
    skills = extract_canonical_skills(sections, "")
    names = {item["canonical"].lower() for item in skills}
    assert "python" in names
    assert "sql" in names


def test_parse_date_range_months_handles_present():
    tenure = parse_date_range_months("2024.09-至今")
    assert tenure["months"] >= 1
    assert tenure["start_date"].startswith("2024-09")


def test_experience_months_merge_overlapping_ranges():
    from app.services.structured_extract import _merged_interval_months
    from datetime import date

    # 2023.01-2023.12 与 2023.06-2024.03 重叠，合并后约 15 个月而非 22
    months = _merged_interval_months(
        [
            (date(2023, 1, 1), date(2023, 12, 1)),
            (date(2023, 6, 1), date(2024, 3, 1)),
        ]
    )
    assert months == 15


def test_implicit_skills_from_experience():
    sections = {
        "skills": ["沟通表达"],
        "projects": ["使用 Python 与 SQL 完成数据分析看板"],
        "internship": [],
        "campus": [],
    }
    skills = extract_canonical_skills(sections, "")
    implicit = [item for item in skills if item.get("source") == "implicit"]
    names = {item["canonical"].lower() for item in implicit}
    assert "python" in names or "sql" in names


def test_match_job_exposes_ats_and_gap_tiers():
    text = "熟悉 Python 与 Excel，参与数据分析项目，完成报表自动化。"
    result = match_job(
        text,
        ["python", "excel"],
        "数据分析师",
        "要求 Python SQL Excel 可视化",
        "manual",
        sections={"education": ["某某大学"], "skills": ["Python"], "projects": ["数据分析"]},
        structured={"skills": [{"canonical": "Python"}, {"canonical": "Excel"}]},
    )
    assert "ats_breakdown" in result
    assert result["ats_breakdown"]["overall"] >= 0
    assert "critical_gaps" in result
    assert "minor_gaps" in result
