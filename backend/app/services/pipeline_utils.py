"""分析流水线公共工具：板块归一化、关键词匹配等。"""

from __future__ import annotations

import re
from typing import Any

from app.services.score_engine import SECTION_LABELS

CORE_SECTION_KEYS = ("basic_info", "education", "internship", "projects", "skills")
SECTION_DISPLAY_ORDER = (
    "basic_info",
    "summary",
    "education",
    "internship",
    "projects",
    "campus",
    "skills",
    "awards",
)


def label_for_section(key: str) -> str:
    return SECTION_LABELS.get(str(key).lower(), str(key))

SECTION_ALIASES: dict[str, str] = {
    "experience": "internship",
    "work": "internship",
    "work_experience": "internship",
    "employment": "internship",
    "job": "internship",
    "certificate": "awards",
    "certificates": "awards",
    "honor": "awards",
    "honors": "awards",
    "profile": "basic_info",
    "contact": "basic_info",
    "education_background": "education",
    "project": "projects",
    "skill": "skills",
    "campus_experience": "campus",
}

EXPERIENCE_SECTION_KEYS = ("internship", "projects", "campus", "work", "experience")

KEYWORD_SYNONYMS: dict[str, list[str]] = {
    "python": ["py", "python3"],
    "javascript": ["js", "es6", "typescript", "ts"],
    "java": [],
    "vue": ["vue.js", "vue3"],
    "react": ["react.js", "reactjs"],
    "mysql": ["sql"],
    "excel": ["wps表格"],
    "数据分析": ["数据运营", "数据挖掘"],
    "产品经理": ["产品助理", "产品实习"],
    "前端": ["前端开发", "web前端"],
    "后端": ["后端开发", "服务端"],
}


def normalize_sections(sections: dict[str, list[str]]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for key, lines in (sections or {}).items():
        if not isinstance(lines, list):
            continue
        canonical = SECTION_ALIASES.get(str(key).lower(), str(key).lower())
        bucket = normalized.setdefault(canonical, [])
        for line in lines:
            text = str(line).strip()
            if text and text not in bucket:
                bucket.append(text)
    return normalized


def expand_keyword_variants(word: str) -> set[str]:
    base = word.strip().lower()
    if not base:
        return set()
    variants = {base}
    for key, aliases in KEYWORD_SYNONYMS.items():
        if base == key or base in aliases:
            variants.add(key)
            variants.update(aliases)
    return {item for item in variants if item}


def resume_contains_keyword(resume_lower: str, word: str) -> bool:
    token = word.strip().lower()
    if not token:
        return False
    if re.fullmatch(r"[a-z+#.]{2,}", token):
        pattern = rf"(?<![a-z0-9+#.]){re.escape(token)}(?![a-z0-9+#.])"
        return bool(re.search(pattern, resume_lower))
    return token in resume_lower


def collect_experience_lines(sections: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for key in EXPERIENCE_SECTION_KEYS:
        for line in sections.get(key, []) or []:
            text = re.sub(r"\s+", " ", str(line)).strip()
            if text and text not in seen:
                seen.add(text)
                lines.append(text)
    return lines


def compact_evidence_pack(result: dict[str, Any], resume_text: str, limit: int = 2600) -> dict[str, Any]:
    evidence = result.get("evidence") or {}
    match_result = result.get("match_result") or {}
    prioritized = _prioritize_resume_text(resume_text, limit)
    return {
        "target_position": result.get("target_position", ""),
        "target_source": result.get("target_position_source", ""),
        "parse_quality": result.get("parse_quality", "medium"),
        "parse_warnings": (result.get("parse_warnings") or [])[:5],
        "total_score": result.get("total_score"),
        "scores": result.get("scores", {}),
        "missing_keywords": (match_result.get("missing_keywords") or [])[:10],
        "matched_keywords": (match_result.get("matched_keywords") or [])[:10],
        "weak_experience_lines": (evidence.get("weak_experience_lines") or [])[:5],
        "vague_lines": (evidence.get("vague_lines") or [])[:3],
        "sample_metric_lines": (evidence.get("sample_metric_lines") or [])[:3],
        "missing_sections": evidence.get("missing_sections") or [],
        "resume_excerpt": prioritized,
    }


def _prioritize_resume_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    lines = text.splitlines()
    priority: list[str] = []
    tail: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(
            token in stripped
            for token in ("实习", "项目", "负责", "参与", "技能", "教育", "大学", "专业", "Python", "Java")
        ):
            priority.append(stripped)
        else:
            tail.append(stripped)
    merged = "\n".join(priority + tail)
    return merged[:limit]
