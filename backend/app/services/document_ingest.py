"""文档接入层：统一简历文件读取入口。"""

from pathlib import Path

from app.services.parser import parse_resume
from app.services.pipeline_utils import CORE_SECTION_KEYS, SECTION_DISPLAY_ORDER, label_for_section, normalize_sections


def ingest_resume(path: Path) -> dict:
    """解析简历并返回平台标准结构。"""
    parsed = parse_resume(path)
    sections = normalize_sections(parsed.get("sections", {}))
    parsed["sections"] = sections
    warnings = parsed.get("parse_warnings") or parsed.get("warnings", [])
    quality = parsed.get("parse_quality", "medium")
    confidence_map = {"high": 0.9, "medium": 0.72, "low": 0.45}
    base_confidence = confidence_map.get(quality, 0.6)
    return {
        **parsed,
        "entities": {
            "target_position": parsed.get("detected_target_position", ""),
            "keywords": parsed.get("detected_keywords", []),
            "name": parsed.get("name_hint", ""),
            **(parsed.get("contact_entities") or {}),
        },
        "blocks": _build_blocks(sections, quality, base_confidence),
        "missing_sections": [key for key in CORE_SECTION_KEYS if not sections.get(key)],
        "warnings": warnings,
        "confidence": base_confidence,
    }


def _build_blocks(sections: dict[str, list[str]], quality: str, base_confidence: float) -> list[dict]:
    blocks: list[dict] = []
    ordered_keys = [key for key in SECTION_DISPLAY_ORDER if sections.get(key)]
    ordered_keys.extend(key for key in sections if key not in ordered_keys and sections.get(key))
    for key in ordered_keys:
        lines = sections.get(key) or []
        if not lines:
            continue
        confidence = _block_confidence(key, lines, quality, base_confidence)
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
            }
        )
    return blocks


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "识别较完整"
    if confidence >= 0.65:
        return "基本识别"
    return "识别偏弱"


def _block_confidence(section: str, lines: list[str], quality: str, base: float) -> float:
    if quality == "low":
        return round(min(base, 0.5), 2)
    line_bonus = min(0.08, len(lines) * 0.02)
    core_sections = {"internship", "projects", "education", "skills"}
    section_bonus = 0.05 if section in core_sections else 0.0
    return round(min(0.98, base + line_bonus + section_bonus), 2)
