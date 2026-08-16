"""文档接入层：统一简历文件读取入口。"""

from pathlib import Path

from app.services.parser import parse_resume
from app.services.pipeline_utils import CORE_SECTION_KEYS, SECTION_DISPLAY_ORDER, label_for_section, normalize_sections
from app.services.structured_extract import extract_structured_profile


def ingest_resume(path: Path) -> dict:
    """解析简历并返回平台标准结构。"""
    parsed = parse_resume(path)
    sections = normalize_sections(parsed.get("sections", {}))
    parsed["sections"] = sections
    warnings = parsed.get("parse_warnings") or parsed.get("warnings", [])
    quality = parsed.get("parse_quality", "medium")
    confidence_map = {"high": 0.9, "medium": 0.72, "low": 0.45}
    base_confidence = confidence_map.get(quality, 0.6)
    structured = extract_structured_profile(sections, parsed.get("raw_text") or "")
    keywords = _merge_keywords(parsed.get("detected_keywords") or [], structured)
    parsed["detected_keywords"] = keywords
    return {
        **parsed,
        "structured": structured,
        "entities": {
            "target_position": parsed.get("detected_target_position", ""),
            "keywords": keywords,
            "name": parsed.get("name_hint", ""),
            "structured": structured,
            **(parsed.get("contact_entities") or {}),
        },
        "blocks": _build_blocks(sections, quality, base_confidence, structured),
        "missing_sections": [key for key in CORE_SECTION_KEYS if not sections.get(key)],
        "warnings": warnings,
        "confidence": base_confidence,
    }


def _merge_keywords(base: list[str], structured: dict) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in list(base) + [str(s.get("canonical") or s.get("name") or "") for s in structured.get("skills") or []]:
        word = str(item or "").strip()
        if not word:
            continue
        key = word.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(word)
    return merged[:40]


def _build_blocks(
    sections: dict[str, list[str]],
    quality: str,
    base_confidence: float,
    structured: dict | None = None,
) -> list[dict]:
    blocks: list[dict] = []
    structured = structured or {}
    ordered_keys = [key for key in SECTION_DISPLAY_ORDER if sections.get(key)]
    ordered_keys.extend(key for key in sections if key not in ordered_keys and sections.get(key))
    for key in ordered_keys:
        lines = sections.get(key) or []
        if not lines:
            continue
        confidence = _block_confidence(key, lines, quality, base_confidence, structured)
        preview = next((line.strip() for line in lines if str(line).strip()), "")
        blocks.append(
            {
                "section": key,
                "section_label": label_for_section(key),
                "lines": lines,
                "line_count": len(lines),
                "preview": preview[:120],
                "confidence": confidence,
                "confidence_label": _confidence_label(confidence),
                "structured_count": _structured_count(key, structured),
            }
        )
    return blocks


def _structured_count(section: str, structured: dict) -> int:
    if section == "education":
        return len(structured.get("education") or [])
    if section in {"internship", "projects", "campus"}:
        return len([item for item in structured.get("experience") or [] if item.get("section") == section])
    if section == "awards":
        return len(structured.get("awards") or [])
    if section == "skills":
        return len(structured.get("skills") or [])
    return 0


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "识别较完整"
    if confidence >= 0.65:
        return "基本识别"
    return "识别偏弱"


def _block_confidence(
    section: str,
    lines: list[str],
    quality: str,
    base: float,
    structured: dict | None = None,
) -> float:
    if quality == "low":
        return round(min(base, 0.5), 2)
    line_bonus = min(0.08, len(lines) * 0.02)
    core_sections = {"internship", "projects", "education", "skills"}
    section_bonus = 0.05 if section in core_sections else 0.0
    struct_bonus = 0.04 if _structured_count(section, structured or {}) > 0 else 0.0
    return round(min(0.98, base + line_bonus + section_bonus + struct_bonus), 2)
