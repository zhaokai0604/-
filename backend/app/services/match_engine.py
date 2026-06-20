"""岗位匹配引擎：关键词检索 + 岗位画像匹配。"""

from __future__ import annotations

import re
from typing import Any

from app.services.score_engine import JOB_PROFILES


def match_job(text: str, keywords: list[str], target_position: str, job_description: str, target_source: str) -> dict[str, Any]:
    source = f"{target_position}\n{job_description}".lower()
    resume = text.lower()
    profile_name, profile = _select_job_profile(source)
    expected: set[str] = set()
    focus: list[str] = []
    if profile:
        expected.update(word.lower() for word in profile["keywords"])
        focus = list(profile["focus"])
    jd_words = _extract_job_words(job_description)
    expected.update(jd_words)
    if target_position:
        expected.update(word.lower() for word in re.findall(r"[A-Za-z+#.]{2,}|[\u4e00-\u9fa5]{2,}", target_position))
    if not expected:
        expected.update(word.lower() for word in keywords[:12])

    matched = sorted(word for word in expected if word and word in resume)
    missing = sorted(word for word in expected if word and word not in resume)[:12]
    if not expected:
        return {
            "score": 70,
            "target_position": "",
            "target_source": "generic",
            "profile": "",
            "matched_keywords": [],
            "missing_keywords": [],
            "focus_suggestions": [],
            "evidence_snippets": [],
            "confidence": 0.5,
            "summary": "未提供目标岗位，使用通用求职匹配规则。",
        }
    score = round(min(100, max(35, len(matched) / max(len(expected), 1) * 100)))
    if profile and matched:
        score = min(100, score + 6)
    source_label = {"manual": "手动输入岗位", "detected": "简历识别岗位", "generic": "通用规则"}[target_source]
    evidence_snippets = _collect_evidence_snippets(text, matched[:8])
    confidence = round(min(0.95, 0.45 + len(matched) / max(len(expected), 1) * 0.5), 2)
    return {
        "score": score,
        "target_position": target_position,
        "target_source": target_source,
        "profile": profile_name,
        "matched_keywords": matched[:15],
        "missing_keywords": missing,
        "focus_suggestions": focus,
        "evidence_snippets": evidence_snippets,
        "confidence": confidence,
        "summary": f"{source_label}：{target_position or '未识别'}。已匹配 {len(matched)} 个岗位关键词，缺少 {len(missing)} 个关键词表达。",
    }


def _collect_evidence_snippets(text: str, keywords: list[str]) -> list[dict[str, str]]:
    snippets: list[dict[str, str]] = []
    for line in text.splitlines():
        normalized = line.strip()
        if len(normalized) < 8:
            continue
        lowered = normalized.lower()
        for keyword in keywords:
            if keyword in lowered:
                snippets.append({"keyword": keyword, "text": normalized[:120]})
                break
        if len(snippets) >= 5:
            break
    return snippets


def _select_job_profile(source: str) -> tuple[str, dict[str, Any] | None]:
    for name, profile in JOB_PROFILES.items():
        if any(alias.lower() in source for alias in profile["aliases"]):
            return name, profile
    return "", None


def _extract_job_words(job_description: str) -> set[str]:
    words = set(word.lower() for word in re.findall(r"[A-Za-z+#.]{2,}|[\u4e00-\u9fa5]{2,}", job_description))
    stopwords = {
        "岗位", "职责", "要求", "优先", "具备", "相关", "能力", "工作", "负责", "完成", "进行", "以及", "通过",
        "我们", "公司", "经验", "良好", "熟悉", "使用", "协助", "参与", "以上", "本科", "大专",
    }
    return {word for word in words if word not in stopwords and len(word) <= 16}
