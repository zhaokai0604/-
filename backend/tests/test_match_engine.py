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


def test_match_job_evidence_is_section_grounded():
    result = match_job(
        "基本信息\n张三\n技能\nPython SQL\n项目\n负责 Python 数据分析看板",
        [],
        "数据分析师",
        "要求 Python SQL 可视化 沟通 积极 主动 团队",
        "manual",
        sections={
            "basic_info": ["张三"],
            "skills": ["Python SQL"],
            "projects": ["负责 Python 数据分析看板"],
        },
    )
    assert result["evidence_snippets"]
    assert any(item.get("section") in {"skills", "projects"} for item in result["evidence_snippets"])
    # 软词不应大量进入 critical_gaps
    soft = {"沟通", "积极", "主动", "团队"}
    assert not soft.issubset(set(result.get("critical_gaps") or []))


def test_jd_noise_words_not_forced_as_must_gaps():
    result = match_job(
        "使用 Python 完成报表",
        [],
        "数据分析",
        "岗位职责：负责完成相关工作，要求积极主动，具备良好沟通能力，熟悉 Python",
        "manual",
    )
    missing = set(result.get("missing_keywords") or [])
    assert "积极" not in missing
    assert "主动" not in missing
    assert "沟通" not in (result.get("critical_gaps") or [])


def test_jd_description_does_not_turn_plain_chinese_into_keyword_gaps():
    result = match_job(
        "使用 Python 完成报表",
        [],
        "数据分析师",
        "负责日常工作，保持责任心，配合团队完成任务，欢迎应届生加入",
        "manual",
    )
    missing = set(result.get("missing_keywords") or [])
    assert not {"日常工作", "责任心", "完成任务", "应届生"} & missing


def test_profile_focus_and_role_title_are_not_missing_keywords():
    result = match_job(
        "使用 Python 完成报表",
        [],
        "数据分析师",
        "",
        "manual",
    )
    missing = set(result.get("missing_keywords") or [])
    assert "数据分析师" not in missing
    assert "突出数据处理工具" not in missing
