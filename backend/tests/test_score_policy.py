"""Tests for low-parse scoring policy."""

from app.services.scoring import analyze_resume


def test_low_parse_quality_caps_total_score():
    parsed = {
        "raw_text": "少量文字",
        "sections": {"basic_info": ["张三"]},
        "detected_keywords": [],
        "parse_quality": "low",
        "parse_warnings": ["正文提取不足"],
    }
    result = analyze_resume(parsed, "数据分析师", "Python SQL")
    assert result["total_score"] <= 58
    assert result.get("score_reliability") == "low_parse_capped"
    assert any("正文提取不足" in item for item in result["diagnosis"])
