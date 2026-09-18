from app.api.serializers import public_analysis_mode_label
from app.services.ai import _parse_deepseek_json
from app.services.analysis_pipeline import resolve_effective_ai, run_analysis_pipeline


def test_public_analysis_mode_label_hides_internal_core_when_ai_requested():
    sections = {"_ai_requested": True, "_ai_enhancement_status": "pending"}

    assert public_analysis_mode_label("core", sections) == "增强分析进行中"


def test_public_analysis_mode_label_marks_completed_ai_enhancement():
    sections = {"_ai_requested": True, "_ai_enhancement_status": "success"}

    assert public_analysis_mode_label("core", sections) == "增强分析已完成"


def test_parse_deepseek_json_tolerates_surrounding_text():
    payload = _parse_deepseek_json('以下是结果：\n{"diagnosis": ["经历可量化"], "suggestions": []}\n请查收。')

    assert payload["diagnosis"] == ["经历可量化"]


def test_parse_deepseek_json_tolerates_trailing_commas():
    payload = _parse_deepseek_json('```json\n{"diagnosis": ["经历可量化",], "suggestions": [],}\n```')

    assert payload["diagnosis"] == ["经历可量化"]


def test_resolve_effective_ai_disabled_when_not_requested():
    enabled, reason = resolve_effective_ai(False, "high", 1)
    assert enabled is False
    assert reason is None


def test_resolve_effective_ai_skips_low_parse():
    enabled, reason = resolve_effective_ai(True, "low", 1)
    assert enabled is False
    assert reason and "跳过 AI" in reason


def test_resolve_effective_ai_skips_large_batch():
    enabled, reason = resolve_effective_ai(True, "high", 12)
    assert enabled is False
    assert reason and "12" in reason


def test_resolve_effective_ai_allows_normal_case():
    enabled, reason = resolve_effective_ai(True, "medium", 3)
    assert enabled is True
    assert reason is None


def test_run_analysis_pipeline_defers_ai_and_keeps_rule_rewrite(monkeypatch, tmp_path):
    def fake_ingest_resume(path):
        return {
            "raw_text": "Python SQL 数据分析项目\n负责日常数据分析工作",
            "sections": {"skills": ["Python", "SQL"], "internship": ["负责日常数据分析工作"]},
            "blocks": [{"section": "skills", "lines": ["Python"]}],
            "entities": {},
            "missing_sections": [],
            "parse_quality": "high",
            "parse_warnings": [],
        }

    def fake_analyze_resume(parsed, target_position, job_description, **kwargs):
        return {
            "target_position": target_position,
            "total_score": 82,
            "scores": {"experience_match": 72, "job_match": 80},
            "sections": parsed["sections"],
            "diagnosis": ["经历描述可以更量化"],
            "suggestions": ["补充项目指标"],
            "structured_suggestions": [],
            "match_result": {"target_position": target_position, "missing_keywords": ["Excel"], "matched_keywords": ["Python"]},
            "evidence": {
                "weak_experience_lines": ["负责日常数据分析工作"],
                "vague_lines": [],
                "long_lines": [],
                "sample_metric_lines": [],
                "metric_line_count": 0,
                "missing_sections": [],
            },
            "parse_quality": "high",
            "parse_warnings": [],
            "weight_template": "default",
            "score_reliability": "normal",
        }

    monkeypatch.setattr("app.services.analysis_pipeline.ingest_resume", fake_ingest_resume)
    monkeypatch.setattr("app.services.analysis_pipeline.analyze_resume", fake_analyze_resume)

    result = run_analysis_pipeline(tmp_path / "cv.docx", "数据分析师", "", True)

    assert result["mode"] == "core"
    assert result["sections_payload"]["_ai_requested"] is True
    assert result["sections_payload"]["_ai_enhancement_status"] == "pending"
    assert result["sections_payload"]["_rewrite_preview"]["mode"] == "offline_star"
    assert result["sections_payload"]["_rewrite_preview"]["items"]
    assert result["sections_payload"]["_interview_prep"] == {}
    assert result["sections_payload"]["_mock_interview"] == {}


def test_run_analysis_pipeline_skips_ai_for_low_parse_but_keeps_rule_rewrite(monkeypatch, tmp_path):
    def fake_ingest_resume(path):
        return {
            "raw_text": "",
            "sections": {},
            "blocks": [],
            "entities": {},
            "missing_sections": [],
            "parse_quality": "low",
            "parse_warnings": ["正文提取不足"],
        }

    def fake_analyze_resume(parsed, target_position, job_description, **kwargs):
        return {
            "target_position": target_position,
            "total_score": 40,
            "scores": {"experience_match": 40, "job_match": 40},
            "sections": {},
            "diagnosis": ["正文提取不足"],
            "suggestions": ["改用标准 DOCX"],
            "structured_suggestions": [],
            "match_result": {"target_position": target_position, "missing_keywords": []},
            "evidence": {"missing_sections": [], "metric_line_count": 0},
            "parse_quality": "low",
            "parse_warnings": ["正文提取不足"],
            "weight_template": "default",
            "score_reliability": "low_parse_capped",
        }

    def fail_enhance(*args, **kwargs):
        raise AssertionError("AI should be skipped for low parse quality")

    monkeypatch.setattr("app.services.analysis_pipeline.ingest_resume", fake_ingest_resume)
    monkeypatch.setattr("app.services.analysis_pipeline.analyze_resume", fake_analyze_resume)

    result = run_analysis_pipeline(tmp_path / "bad.pdf", "数据分析师", "", True)

    assert result["mode"] == "core"
    assert "跳过 AI" in result["sections_payload"]["_ai_skip_reason"]
    assert result["sections_payload"]["_ai_enhancement_status"] == "failed"
    assert result["sections_payload"]["_rewrite_preview"]["mode"] == "offline_star"


def test_run_analysis_pipeline_empty_target_does_not_auto_adopt(monkeypatch, tmp_path):
    """空目标岗只推荐、不采用，匹配结果应为通用。"""

    def fake_ingest_resume(path):
        return {
            "raw_text": "熟悉 C语言 与单片机，做过智能硬件小项目",
            "sections": {"skills": ["C语言", "单片机"], "projects": ["智能硬件小项目"]},
            "blocks": [],
            "entities": {"target_position": "嵌入式开发实习生"},
            "detected_target_position": "嵌入式开发实习生",
            "missing_sections": [],
            "parse_quality": "high",
            "parse_warnings": [],
        }

    def fake_select_job(*args, **kwargs):
        return {
            "matched": True,
            "fallback_used": False,
            "recommendation_only": False,
            "adopted_as_target": True,
            "target_position": "嵌入式开发实习生",
            "job_description": "要求 C++",
            "company": "示例公司",
            "related_jobs": [
                {"rank": 1, "target_position": "嵌入式开发实习生", "match_score": 0.44, "id": "job-1"},
            ],
            "match_score": 0.44,
            "matched_keywords": ["C语言"],
            "quality_warning": "should be overwritten",
        }

    def fake_analyze_resume(parsed, target_position, job_description, **kwargs):
        assert target_position == ""
        assert job_description == ""
        assert kwargs.get("allow_detected") is False
        assert parsed.get("detected_target_position") == ""
        return {
            "target_position": "",
            "target_position_source": "generic",
            "total_score": 70,
            "scores": {"experience_match": 70, "job_match": 50},
            "sections": parsed["sections"],
            "diagnosis": [],
            "suggestions": [],
            "structured_suggestions": [],
            "match_result": {
                "target_position": "",
                "target_source": "generic",
                "missing_keywords": [],
                "matched_keywords": [],
                "summary": "未提供目标岗位或 JD",
            },
            "evidence": {
                "weak_experience_lines": [],
                "vague_lines": [],
                "long_lines": [],
                "sample_metric_lines": [],
                "metric_line_count": 0,
                "missing_sections": [],
            },
            "parse_quality": "high",
            "parse_warnings": [],
            "weight_template": "default",
            "score_reliability": "normal",
        }

    monkeypatch.setattr("app.services.analysis_pipeline.ingest_resume", fake_ingest_resume)
    monkeypatch.setattr("app.services.analysis_pipeline.select_job_for_resume", fake_select_job)
    monkeypatch.setattr("app.services.analysis_pipeline.analyze_resume", fake_analyze_resume)

    result = run_analysis_pipeline(tmp_path / "cv.docx", "", "", False)
    market = result["sections_payload"]["_job_market_match"]
    assert market["adopted_as_target"] is False
    assert market["recommendation_only"] is True
    assert market["matched"] is False
    assert market["target_position"] == ""
    assert market["related_jobs"]
    assert result["target_position"] == ""
    assert result["result"]["match_result"]["target_source"] == "generic"
