import json
import re
from typing import Any

from app.services.ai_http import post_ai_json
from app.services.runtime_config import get_ai_runtime_config
from app.services.suggestion_engine import build_structured_suggestions


def enhance_with_deepseek(result: dict[str, Any], resume_text: str, enable_ai: bool) -> tuple[dict[str, Any], str]:
    """Enhance diagnosis and rewrite preview with a single model call."""
    from app.services.pipeline_utils import compact_evidence_pack

    ai_config = get_ai_runtime_config()
    if not enable_ai:
        return result, "core"
    if not ai_config["api_key"]:
        result["ai_fallback_reason"] = "未配置 DEEPSEEK_API_KEY，已自动使用规则诊断与规则改写。"
        return result, "offline_fallback"

    target_position = (result.get("target_position") or "").strip()
    target_source = result.get("target_position_source", "generic")
    source_label = {
        "manual": "手动输入岗位",
        "detected": "简历识别岗位",
        "generic": "通用建议",
    }.get(target_source, "通用建议")

    evidence_pack = compact_evidence_pack(result, resume_text)
    offline_diagnosis = result.get("diagnosis") or []
    offline_suggestions = result.get("suggestions") or []
    base_rewrite = result.get("rewrite_preview") if isinstance(result.get("rewrite_preview"), dict) else {}
    rewrite_samples = [
        {
            "section": item.get("section", ""),
            "original": item.get("original", ""),
            "suggested": item.get("suggested", ""),
            "focus": item.get("focus", ""),
        }
        for item in (base_rewrite.get("items") or [])[:5]
        if isinstance(item, dict)
    ]

    prompt = (
        "You are a Chinese resume optimization expert for university students. "
        "Return JSON only, no Markdown. Improve both diagnosis and rewrite output in one response.\n"
        "Required JSON fields:\n"
        "- diagnosis: string[] of concrete problems.\n"
        "- suggestions: string[] of executable changes.\n"
        "- structured: array of objects with problem/evidence/impact/direction/example.\n"
        "- rewrite_preview: object with summary and items. items must contain section/original/suggested/focus.\n"
        "Rules:\n"
        "1. Write all user-facing content in Simplified Chinese.\n"
        "2. Cite concrete resume evidence. Do not invent metrics; use __ placeholders when data is missing.\n"
        "3. Merge and sharpen the offline findings instead of repeating them verbatim.\n"
        "4. Rewrite items must be complete resume-ready sentences, not abstract advice.\n"
        "5. If parse_quality is low, only give file/format advice and do not invent experience.\n\n"
        f"Target position: {target_position or 'none'}\n"
        f"Target source: {source_label}\n"
        f"Evidence pack: {json.dumps(evidence_pack, ensure_ascii=False)}\n"
        f"Offline diagnosis: {json.dumps(offline_diagnosis[:6], ensure_ascii=False)}\n"
        f"Offline suggestions: {json.dumps(offline_suggestions[:6], ensure_ascii=False)}\n"
        f"Rule rewrite base: {json.dumps(rewrite_samples, ensure_ascii=False)}\n"
        f"Resume excerpt: {resume_text[:1800]}\n"
    )
    try:
        response = post_ai_json(
            ai_config["api_url"],
            headers={"Authorization": f"Bearer {ai_config['api_key']}", "Content-Type": "application/json"},
            payload={
                "model": ai_config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.32,
                "max_tokens": 1800,
            },
            timeout=35,
            attempts=2,
        )
        content = response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        result["ai_fallback_reason"] = f"DeepSeek 调用失败，已自动使用规则诊断与规则改写：{exc}"
        return result, "offline_fallback"

    try:
        enhanced = _parse_deepseek_json(content)
    except json.JSONDecodeError:
        result["ai_fallback_reason"] = "DeepSeek 返回内容不是有效 JSON，已自动使用规则诊断与规则改写。"
        return result, "offline_fallback"

    result["diagnosis"] = _merge_unique_strings(offline_diagnosis, enhanced.get("diagnosis"))
    result["suggestions"] = _merge_unique_strings(offline_suggestions, enhanced.get("suggestions"))

    ai_structured = enhanced.get("structured")
    if isinstance(ai_structured, list) and ai_structured:
        offline_structured = result.get("structured_suggestions") or []
        result["structured_suggestions"] = _merge_structured(offline_structured, ai_structured)
    elif not result.get("structured_suggestions"):
        result["structured_suggestions"] = build_structured_suggestions(
            result.get("scores", {}),
            result.get("sections", {}),
            result.get("match_result", {}),
            result.get("parse_quality", "medium"),
            result.get("evidence", {}),
        )

    rewrite_preview = _normalize_rewrite_preview(
        enhanced.get("rewrite_preview") or enhanced.get("rewrite"),
        base_rewrite,
        target_position,
    )
    if rewrite_preview:
        result["rewrite_preview"] = rewrite_preview

    return result, "deepseek"


def _merge_unique_strings(base: list[str], incoming: Any, limit: int = 12) -> list[str]:
    merged = list(base) if isinstance(base, list) else []
    if isinstance(incoming, list):
        for item in incoming:
            text = str(item).strip()
            if text and text not in merged:
                merged.append(text)
    return merged[:limit]


def _merge_structured(base: list[dict[str, str]], incoming: list[Any], limit: int = 10) -> list[dict[str, str]]:
    merged = [item for item in base if isinstance(item, dict)]
    seen = {item.get("problem", "") for item in merged}
    for item in incoming:
        if not isinstance(item, dict):
            continue
        problem = str(item.get("problem", "")).strip()
        if not problem or problem in seen:
            continue
        seen.add(problem)
        merged.append(
            {
                "problem": problem,
                "evidence": str(item.get("evidence", "")),
                "impact": str(item.get("impact", "")),
                "direction": str(item.get("direction", "")),
                "example": str(item.get("example", "")),
            }
        )
        if len(merged) >= limit:
            break
    return merged


def _normalize_rewrite_preview(incoming: Any, fallback: dict[str, Any], target_position: str) -> dict[str, Any]:
    if not isinstance(incoming, dict):
        return fallback if isinstance(fallback, dict) else {}
    items: list[dict[str, str]] = []
    for item in incoming.get("items") or []:
        if not isinstance(item, dict):
            continue
        original = str(item.get("original", "")).strip()
        suggested = str(item.get("suggested", "")).strip()
        if not original or not suggested or original == suggested:
            continue
        items.append(
            {
                "section": str(item.get("section", "经历")).strip() or "经历",
                "original": original,
                "suggested": suggested,
                "focus": str(item.get("focus", "AI 深度改写")).strip() or "AI 深度改写",
            }
        )
        if len(items) >= 8:
            break
    if not items:
        return fallback if isinstance(fallback, dict) else {}
    return {
        "summary": str(incoming.get("summary") or f"AI 围绕「{target_position or '目标岗位'}」生成 {len(items)} 条改写参考。"),
        "items": items,
        "target_position": str(incoming.get("target_position") or target_position or ""),
        "mode": "deepseek",
    }


def _parse_deepseek_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.S)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    cleaned = cleaned.replace("\ufeff", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            candidate = cleaned[start : end + 1]
            candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
            return json.loads(candidate)
        raise
