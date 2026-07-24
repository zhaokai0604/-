from app.services.resume_rewriter import build_rewrite_preview
from app.services.scoring import analyze_resume
from app.services.suggestion_engine import build_structured_suggestions


def test_analyze_resume_includes_structured_suggestions():
    parsed = {
        "raw_text": "张三\n数据分析师\nPython SQL\n负责数据分析，提升转化率15%",
        "sections": {
            "basic_info": ["张三"],
            "education": ["某大学 统计学"],
            "internship": ["数据分析实习"],
            "projects": ["数据清洗项目"],
            "skills": ["Python", "SQL"],
        },
        "detected_keywords": ["python", "sql"],
        "parse_quality": "medium",
        "parse_warnings": [],
    }
    result = analyze_resume(parsed, "数据分析师", "Python SQL Excel")
    assert result["structured_suggestions"]
    first = result["structured_suggestions"][0]
    assert "problem" in first
    assert "evidence" in first
    assert "example" in first


def test_build_rewrite_preview_has_items():
    evidence = {
        "weak_experience_lines": ["负责日常数据分析工作"],
        "vague_lines": ["熟悉相关工具"],
        "metric_line_count": 0,
        "sample_metric_lines": [],
    }
    preview = build_rewrite_preview(
        {"skills": ["Python", "SQL"]},
        {"target_position": "数据分析师", "missing_keywords": ["excel"]},
        evidence,
        "数据分析师",
    )
    assert preview["items"]
    assert preview["target_position"] == "数据分析师"
    assert preview["mode"] == "offline_star"
    first = preview["items"][0]
    assert first["original"] != first["suggested"]
    assert "STAR" in first["focus"] or "关键词" in first["focus"] or "结果" in first["focus"]


def test_build_rewrite_preview_leads_with_metric():
    evidence = {
        "weak_experience_lines": [],
        "vague_lines": [],
        "sample_metric_lines": ["负责数据分析，提升转化率15%"],
        "metric_line_count": 1,
    }
    preview = build_rewrite_preview(
        {"skills": ["Python"]},
        {"target_position": "数据分析师", "missing_keywords": []},
        evidence,
        "数据分析师",
    )
    assert preview["items"]
    suggested = preview["items"][0]["suggested"]
    assert "15%" in suggested
    assert suggested.index("15%") < len(suggested) // 2 + 10


def test_build_rewrite_preview_differs_from_diagnosis_style():
    evidence = {
        "weak_experience_lines": ["负责日常数据分析工作"],
        "vague_lines": ["熟悉相关工具"],
        "metric_line_count": 0,
    }
    preview = build_rewrite_preview(
        {"skills": ["Python", "SQL"]},
        {"target_position": "数据分析师", "missing_keywords": ["excel"]},
        evidence,
        "数据分析师",
    )
    for item in preview["items"]:
        assert len(item["suggested"]) > len(item["original"]) + 10


def test_new_media_offline_suggestions_are_specific():
    evidence = {
        "missing_sections": ["projects"],
        "weak_experience_lines": [],
        "metric_line_count": 0,
        "sample_metric_lines": [],
        "course_lines": ["主修课程：PS、PR、AE、新媒体文案与策划、短视频创作与传播基础、小红书运营、淘宝运营、SEO/SEM"],
        "domain_keywords": ["小红书", "淘宝运营", "SEO", "SEM", "PS", "PR", "AE"],
        "domain_signal_lines": ["主修课程：PS、PR、AE、新媒体文案与策划、短视频创作与传播基础、小红书运营、淘宝运营、SEO/SEM"],
    }
    items = build_structured_suggestions(
        {"experience_match": 76, "job_match": 72, "highlight_strength": 58},
        {"education": evidence["course_lines"]},
        {"target_position": "新媒体运营", "profile": "新媒体运营", "missing_keywords": []},
        "high",
        evidence,
    )
    combined = " ".join(item["example"] + item["direction"] for item in items)
    assert "小红书" in combined or "公众号" in combined
    assert "SEO" in combined or "淘宝运营" in combined
    assert "曝光" in combined or "播放" in combined or "互动" in combined
