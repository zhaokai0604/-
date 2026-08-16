"""Fast resume analysis pipeline.

Interview and report generation remain on demand. Core analysis can optionally
run one synchronous AI enhancement that covers diagnosis and rewrite output.
"""

from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter
from collections.abc import Callable
from typing import Any

from app.api.serializers import job_profile_payload
from app.models.entities import JobProfile
from app.services.document_ingest import ingest_resume
from app.services.job_market import select_job_for_resume
from app.services.optimized_resume import attach_optimized_resume
from app.services.resume_rewriter import build_rewrite_preview
from app.services.resume_template_engine import recommend_resume_templates
from app.services.scoring import analyze_resume
from app.services.skill_graph import build_skill_graph_hints
from app.services.suggestion_engine import build_action_roadmap


logger = logging.getLogger("uvicorn.error")
EventSink = Callable[[str, dict[str, Any]], None]


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
    event_sink: EventSink | None = None,
) -> dict[str, Any]:
    def emit(event: str, data: dict[str, Any] | None = None) -> None:
        if event_sink:
            event_sink(event, data or {})

    pipeline_started = perf_counter()
    target_position, job_description = resolve_job_inputs(target_position, job_description, profile)
    emit("step", {"step": "extract", "message": "正在提取正文与结构…"})
    parse_started = perf_counter()
    parsed = ingest_resume(path)
    parse_ms = (perf_counter() - parse_started) * 1000
    lines = [ln.strip() for ln in str(parsed.get("raw_text") or "").splitlines() if ln.strip()]
    for index, line in enumerate(lines[:24]):
        emit("parse_line", {"index": index, "text": line[:180], "message": f"正在阅读第 {index + 1} 行"})
    for key, values in (parsed.get("sections") or {}).items():
        if isinstance(values, list) and values:
            emit(
                "section_found",
                {
                    "section": key,
                    "sample": str(values[0])[:80],
                    "message": f"正在提取「{key}」… 发现「{str(values[0])[:40]}」",
                },
            )
    structured = parsed.get("structured") if isinstance(parsed.get("structured"), dict) else {}
    market_match = select_job_for_resume(
        str(parsed.get("raw_text") or ""),
        parsed.get("sections") if isinstance(parsed.get("sections"), dict) else {},
        target_position,
        job_description,
    )
    user_supplied_position = bool(str(target_position or "").strip())
    user_supplied_jd = bool(str(job_description or "").strip())
    user_supplied_target = user_supplied_position or user_supplied_jd
    # 只有用户明确写了「目标岗位名」才允许采用岗位库标题；
    # 空表单 / 仅粘贴 JD：绝不把推荐岗自动写成分析目标（避免被标成「手动输入」）。
    adopt_market = bool(user_supplied_position and market_match.get("matched"))
    related_jobs = list(market_match.get("related_jobs") or [])[:5]

    if not user_supplied_position:
        # 未填岗位名：强制通用分析，忽略简历识别意向，避免静默套岗
        parsed = {**parsed, "detected_target_position": ""}
        entities = parsed.get("entities")
        if isinstance(entities, dict):
            parsed["entities"] = {**entities, "target_position": ""}
        if not user_supplied_jd:
            target_position = ""
            job_description = ""

    if adopt_market:
        target_position = str(market_match.get("target_position") or target_position)
        job_description = str(market_match.get("job_description") or job_description)
        market_match = {
            **market_match,
            "adopted_as_target": True,
            "recommendation_only": False,
            "related_jobs": related_jobs,
        }
    else:
        warning = str(market_match.get("quality_warning") or "").strip()
        if not user_supplied_target:
            warning = (
                "未选择目标岗位：已按简历给出相似岗位推荐，未自动采用。"
                "可在结果中点击推荐岗位，查看该岗专属评价。"
            )
        elif user_supplied_jd and not user_supplied_position:
            warning = (
                (warning + " " if warning else "")
                + "已按您粘贴的 JD 做匹配；未自动改写为目标库岗位名。"
            ).strip()
        elif not market_match.get("matched"):
            warning = (
                (warning + " " if warning else "")
                + "岗位库未命中，仍按您填写的目标岗做通用匹配。"
            ).strip()
        market_match = {
            "matched": False,
            "fallback_used": True,
            "adopted_as_target": False,
            "recommendation_only": not user_supplied_target,
            "source_type": "offline_rules_fallback" if not user_supplied_target else market_match.get("source_type", "offline_rules_fallback"),
            "review_status": "not_applicable",
            "match_score": market_match.get("match_score", 0),
            "matched_keywords": market_match.get("matched_keywords") or [],
            "evidence_coverage": market_match.get("evidence_coverage", 0),
            "match_explanation": {},
            "requirement_basis": {},
            "target_position": target_position if user_supplied_position else "",
            "job_description": job_description if user_supplied_jd else "",
            "related_jobs": related_jobs,
            "quality_warning": warning,
        }
    parsed["job_market_match"] = market_match
    emit(
        "job_match",
        {
            "target_position": target_position if user_supplied_position else "",
            "source_type": market_match.get("source_type", "offline_rules_fallback"),
            "fallback_used": bool(market_match.get("fallback_used")),
            "match_score": market_match.get("match_score", 0),
            "message": (
                f"岗位库已匹配并采用：{target_position}"
                if adopt_market
                else (
                    f"未指定目标岗：已推荐 {len(related_jobs)} 个相似岗位，未自动采用"
                    if not user_supplied_target
                    else (
                        f"按您填写的目标岗分析；下方推荐仅供参考"
                        if related_jobs
                        else "按您填写的目标岗做匹配分析"
                    )
                )
            ),
            "related_jobs": related_jobs,
            "recommendation_only": bool(market_match.get("recommendation_only")),
        },
    )
    stats = structured.get("stats") if isinstance(structured.get("stats"), dict) else {}
    if stats:
        emit(
            "structured",
            {
                "education_count": stats.get("education_count", 0),
                "experience_count": stats.get("experience_count", 0),
                "skill_count": stats.get("skill_count", 0),
                "award_count": stats.get("award_count", 0),
                "message": (
                    f"结构化抽取完成：教育 {stats.get('education_count', 0)} 条 / "
                    f"经历 {stats.get('experience_count', 0)} 段 / "
                    f"技能 {stats.get('skill_count', 0)} 项"
                ),
            },
        )

    emit("step", {"step": "score", "message": "正在计算六维评分、语义匹配与低信噪比…"})
    rules_started = perf_counter()
    result = analyze_resume(
        parsed,
        target_position,
        job_description,
        allow_detected=user_supplied_position,
    )
    # 最终安全闸：未填写目标岗位时，不能让解析出的「求职意向」重新成为采用岗位。
    # 这层保护防止后续评分/解析模块改动时再次出现静默套岗。
    if not user_supplied_position:
        target_position = ""
        result["target_position"] = ""
        result["target_position_source"] = "generic"
        result_match = result.get("match_result")
        if isinstance(result_match, dict):
            result_match["target_position"] = ""
            result_match["target_source"] = "generic"
            result_match["profile"] = "generic"
            result_match["summary"] = "未指定目标岗位，本次仅进行通用简历分析；下方岗位仅供推荐，不会自动套用。"
    result["job_market_match"] = market_match
    match_result = result.get("match_result", {}) if isinstance(result.get("match_result"), dict) else {}
    sections = result.get("sections", {}) if isinstance(result.get("sections"), dict) else parsed.get("sections", {}) or {}
    evidence = result.get("evidence", {}) if isinstance(result.get("evidence"), dict) else {}
    resolved_target = str(result.get("target_position", target_position) or target_position)

    for word in (match_result.get("matched_keywords") or [])[:8]:
        emit("keyword_hit", {"keyword": word, "message": f"命中岗位关键词「{word}」"})
    for word in (match_result.get("missing_keywords") or [])[:8]:
        emit("keyword_miss", {"keyword": word, "message": f"缺失岗位关键词「{word}」"})
    if match_result.get("semantic_score"):
        emit(
            "semantic",
            {
                "score": match_result.get("semantic_score"),
                "rule_score": match_result.get("rule_score"),
                "message": (
                    f"语义分 {match_result.get('semantic_score')}，"
                    f"规则分 {match_result.get('rule_score')}，融合后 {match_result.get('score')}"
                ),
            },
        )
    for zone in (result.get("low_snr_zones") or [])[:5]:
        if isinstance(zone, dict):
            emit(
                "low_snr",
                {
                    "text": str(zone.get("text") or "")[:120],
                    "reason": zone.get("reason") or "",
                    "message": f"标记低信噪比：{str(zone.get('text') or '')[:40]}",
                },
            )

    emit("step", {"step": "optimize", "message": "正在生成基于初稿的优化稿…"})
    rewrite_preview = build_rewrite_preview(sections, match_result, evidence, resolved_target)
    skill_graph = build_skill_graph_hints(
        str(parsed.get("raw_text") or ""),
        match_result.get("matched_keywords") or [],
        match_result.get("missing_keywords") or [],
        resolved_target,
    )
    for hint in skill_graph.get("hints") or []:
        emit("skill_hint", {"message": hint.get("message"), "hint": hint})
    rewrite_preview = attach_optimized_resume(
        rewrite_preview,
        sections,
        skill_hints=skill_graph.get("hints") or [],
    )
    result["rewrite_preview"] = rewrite_preview
    result["skill_graph"] = skill_graph
    # 低信噪比说明写入诊断旁路字段，供详情页展示
    low_snr_penalty = result.get("low_snr_penalty") if isinstance(result.get("low_snr_penalty"), dict) else {}
    if low_snr_penalty.get("reasons"):
        extra = list(result.get("diagnosis") or [])
        for reason in low_snr_penalty["reasons"]:
            if reason not in extra:
                extra.append(reason)
        result["diagnosis"] = extra
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
    for key, value in (result.get("scores") or {}).items():
        emit("score_dim", {"dimension": key, "value": value, "message": f"维度评分 {key} = {value}"})

    sections_payload = dict(sections)
    sections_payload["_parse_quality"] = result.get("parse_quality", parsed.get("parse_quality", "medium"))
    sections_payload["_parse_warnings"] = result.get("parse_warnings", parsed.get("parse_warnings", []))
    sections_payload["_structured_suggestions"] = result.get("structured_suggestions", [])
    sections_payload["_weight_template"] = result.get("weight_template", "default")
    sections_payload["_score_reliability"] = result.get("score_reliability", "normal")
    sections_payload["_layout_complexity"] = result.get("layout_complexity", parsed.get("layout_complexity", 0.0))
    sections_payload["_evidence_coverage"] = result.get("evidence_coverage", 0.0)
    sections_payload["_quality_warnings"] = result.get("quality_warnings", [])
    sections_payload["_ai_skip_reason"] = result.get("ai_skip_reason", "")
    sections_payload["_ai_requested"] = bool(enable_ai)
    sections_payload["_ai_enhancement_status"] = "pending" if effective_ai else ("failed" if enable_ai and ai_skip_reason else "none")
    sections_payload["_ai_enhancement_error"] = ai_skip_reason or ""
    sections_payload["_entities"] = parsed.get("entities", {})
    sections_payload["_job_market_match"] = market_match
    sections_payload["_structured"] = structured
    sections_payload["_missing_sections"] = parsed.get("missing_sections", [])
    sections_payload["_rewrite_preview"] = rewrite_preview
    sections_payload["_skill_graph"] = skill_graph
    sections_payload["_low_snr_zones"] = result.get("low_snr_zones") or evidence.get("low_snr_zones") or []
    sections_payload["_evidence_confidence"] = result.get("evidence_confidence", evidence.get("evidence_confidence", 0.5))
    sections_payload["_low_snr_penalty"] = result.get("low_snr_penalty") or {}
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
