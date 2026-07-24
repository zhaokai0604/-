"""Unit tests for the scoring engine."""

from app.services.score_engine import label_for_score, score_resume


def _sample_parsed() -> dict:
    return {
        "raw_text": "张三\n数据分析师\nPython SQL Excel\n负责数据分析项目，提升转化率15%\n2023年实习于某公司",
        "sections": {
            "basic_info": ["张三", "13800000000", "zhangsan@example.com"],
            "education": ["某某大学 统计学 本科 2022-2026"],
            "internship": ["2023.06-2023.09 某公司 数据分析实习生", "使用 Python 和 SQL 完成报表，提升转化率 15%"],
            "projects": ["校园数据分析项目：清洗 2 万条数据并输出可视化报告"],
            "skills": ["Python", "SQL", "Excel", "Tableau"],
        },
        "detected_keywords": ["python", "sql", "excel", "数据分析"],
        "detected_target_position": "数据分析师",
        "parse_quality": "high",
        "parse_warnings": [],
    }


def test_score_resume_returns_expected_dimensions():
    result = score_resume(_sample_parsed(), "数据分析师", "熟悉 Python、SQL 和 Excel")
    assert 0 <= result["total_score"] <= 100
    for key in (
        "content_completeness",
        "experience_match",
        "language_professionalism",
        "format_standardization",
        "highlight_strength",
        "job_match",
    ):
        assert key in result["scores"]
        assert 0 <= result["scores"][key] <= 100


def test_score_resume_includes_chart_data():
    result = score_resume(_sample_parsed(), "数据分析师", "")
    assert len(result["chart_data"]["bar"]) == 6
    assert result["chart_data"]["bar"][0]["name"] == label_for_score("content_completeness")


def test_score_resume_respects_manual_target_position():
    result = score_resume(_sample_parsed(), "产品经理", "")
    assert result["target_position"] == "产品经理"
    assert result["target_position_source"] == "manual"
