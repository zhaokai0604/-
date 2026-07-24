"""Fast resume analysis pipeline.

Interview and report generation remain on demand. Core analysis can optionally
run one synchronous AI enhancement that covers diagnosis and rewrite output.
"""

from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from app.api.serializers import job_profile_payload
from app.models.entities import JobProfile
from app.services.document_ingest import ingest_resume
from app.services.resume_rewriter import build_rewrite_preview
from app.services.resume_template_engine import recommend_resume_templates
from app.services.scoring import analyze_resume
from app.services.suggestion_engine import build_action_roadmap


logger = logging.getLogger("uvicorn.error")


def resolve_job_inputs(target_position: str, job_description: str, profile: JobProfile | None) -> tuple[str, str]:
    position = target_position.strip()
    description = job_description.strip()
    if profile:
        position = profile.target_position or position or profile.name
        description = profile.requirement_summary or description or profile.description
    return position, description


def resolve_effective_ai(enable_ai: bool, parse_quality: str, batch_file_count: int = 1) -> tuple[bool, str | None]:
    """Return whether a background AI enhancement request should be attempted."""
    if not enable_ai:
        return False, None
    if parse_quality == "low":
        return False, "正文提取不足，已跳过 AI 增强；请改用可选中文本的 DOCX 或文字版 PDF。"
    if batch_file_count > 8:
        return False, f"批量任务含 {batch_file_count} 份简历，为保障速度已自动使用规则分析。"
    return True, None


def run_analysis_pipeline(
    path: Path,
    target_position: str,
    job_description: str,
    enable_ai: bool,
    profile: JobProfile | None = None,
    *,
    batch_file_count: int = 1,
) -> dict[str, Any]:
    pipeline_started = perf_counter()
    target_position, job_description = resolve_job_inputs(target_position, job_description, profile)
    parse_started = perf_counter()
    parsed = ingest_resume(path)
    parse_ms = (perf_counter() - parse_started) * 1000
    rules_started = perf_counter()
    result = analyze_resume(parsed, target_position, job_description)
    match_result = result.get("match_result", {}) if isinstance(result.get("match_result"), dict) else {}
    sections = result.get("sections", {}) if isinstance(result.get("sections"), dict) else parsed.get("sections", {}) or {}
    evidence = result.get("evidence", {}) if isinstance(result.get("evidence"), dict) else {}
    resolved_target = str(result.get("target_position", target_position) or target_position)

    rewrite_preview = build_rewrite_preview(sections, match_result, evidence, resolved_target)
    result["rewrite_preview"] = rewrite_preview
    rules_ms = (perf_counter() - rules_started) * 1000

    effective_ai, ai_skip_reason = resolve_effective_ai(
        enable_ai,
        str(result.get("parse_quality", parsed.get("parse_quality", "medium"))),
        batch_file_count,
    )
    if ai_skip_reason:
        result["ai_skip_reason"] = ai_skip_reason
    mode = "core"
    result["analysis_mode"] = mode

    if profile:
        result["job_profile"] = job_profile_payload(profile)

    template_recommendations = recommend_resume_templates(
        resolved_target,
        str(result.get("weight_template", "default")),
        sections,
        match_result.get("missing_keywords") or [],
    )

    sections_payload = dict(sections)
    sections_payload["_parse_quality"] = result.get("parse_quality", parsed.get("parse_quality", "medium"))
    sections_payload["_parse_warnings"] = result.get("parse_warnings", parsed.get("parse_warnings", []))
    sections_payload["_structured_suggestions"] = result.get("structured_suggestions", [])
    sections_payload["_weight_template"] = result.get("weight_template", "default")
    sections_payload["_score_reliability"] = result.get("score_reliability", "normal")
    sections_payload["_ai_skip_reason"] = result.get("ai_skip_reason", "")
    sections_payload["_ai_requested"] = bool(enable_ai)
    sections_payload["_ai_enhancement_status"] = "pending" if effective_ai else ("failed" if enable_ai and ai_skip_reason else "none")
    sections_payload["_ai_enhancement_error"] = ai_skip_reason or ""
    sections_payload["_entities"] = parsed.get("entities", {})
    sections_payload["_missing_sections"] = parsed.get("missing_sections", [])
    sections_payload["_rewrite_preview"] = rewrite_preview
    sections_payload["_interview_prep"] = {}
    sections_payload["_mock_interview"] = {}
    sections_payload["_template_recommendations"] = template_recommendations
    sections_payload["_action_roadmap"] = build_action_roadmap(
        result.get("scores", {}),
        result.get("structured_suggestions", []),
        match_result,
        str(result.get("parse_quality", "medium")),
        parsed.get("missing_sections", []),
        result.get("diagnosis", []),
    )
    total_ms = (perf_counter() - pipeline_started) * 1000
    logger.info(
        "resume_analysis_timing file=%s enable_ai=%s effective_ai=%s mode=%s parse_quality=%s "
        "parse_ms=%.0f rule_ms=%.0f total_ms=%.0f",
        path.name,
        enable_ai,
        effective_ai,
        mode,
        result.get("parse_quality", parsed.get("parse_quality", "medium")),
        parse_ms,
        rules_ms,
        total_ms,
    )

    return {
        "result": result,
        "sections_payload": sections_payload,
        "mode": mode,
        "target_position": target_position,
        "job_description": job_description,
        "parsed": parsed,
    }
