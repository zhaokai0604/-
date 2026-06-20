"""文档接入层：统一简历文件读取入口。"""

from pathlib import Path

from app.services.parser import parse_resume


def ingest_resume(path: Path) -> dict:
    """解析简历并返回平台标准结构。"""
    parsed = parse_resume(path)
    sections = parsed.get("sections", {})
    warnings = parsed.get("parse_warnings") or parsed.get("warnings", [])
    quality = parsed.get("parse_quality", "medium")
    confidence_map = {"high": 0.9, "medium": 0.72, "low": 0.45}
    return {
        **parsed,
        "entities": {
            "target_position": parsed.get("detected_target_position", ""),
            "keywords": parsed.get("detected_keywords", []),
        },
        "blocks": [
            {"section": key, "lines": lines, "confidence": confidence_map.get(quality, 0.6)}
            for key, lines in sections.items()
            if lines
        ],
        "warnings": warnings,
        "confidence": confidence_map.get(quality, 0.6),
    }
