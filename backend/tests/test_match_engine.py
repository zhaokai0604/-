"""Tests for match engine and pipeline utilities."""

from app.services.match_engine import match_job
from app.services.pipeline_utils import normalize_sections, resume_contains_keyword


def test_resume_contains_keyword_avoids_java_in_javascript():
    assert resume_contains_keyword("proficient in javascript and react", "java") is False
    assert resume_contains_keyword("proficient in java spring", "java") is True


def test_normalize_sections_maps_experience_alias():
    sections = normalize_sections(
        {
            "experience": ["某公司实习"],
            "work": ["重复不应出现"],
            "Project": ["数据分析项目"],
        }
    )
    assert "internship" in sections
    assert "某公司实习" in sections["internship"]
    assert "projects" in sections


def test_match_job_without_target_is_not_inflated():
    result = match_job(
        "python sql data analysis",
        ["python", "sql", "excel"],
        "",
        "",
        "generic",
    )
    assert result["score"] <= 55
    assert "未提供目标岗位" in result["summary"]


def test_match_job_finds_synonym_js_for_javascript_requirement():
    result = match_job(
        "熟悉 vue react js 项目开发",
        [],
        "前端开发",
        "要求 javascript typescript",
        "manual",
    )
    assert "javascript" in result["matched_keywords"] or "js" in result["matched_keywords"]
