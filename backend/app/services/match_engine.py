"""岗位匹配引擎：关键词检索 + 岗位画像匹配（边界匹配 + 同义词）。"""

from __future__ import annotations

import re
from typing import Any

from app.services.pipeline_utils import expand_keyword_variants, resume_contains_keyword
from app.services.score_engine import JOB_PROFILES


def match_job(text: str, keywords: list[str], target_position: str, job_description: str, target_source: str) -> dict[str, Any]:
    source = f"{target_position}\n{job_description}".lower()
    resume = text.lower()
    profile_name, profile = _select_job_profile(source)
    expected: dict[str, set[str]] = {"must": set(), "nice": set()}

    if profile:
        for word in profile["keywords"]:
            expected["must"].add(word.lower())
        for word in profile.get("focus", []):
            expected["nice"].add(str(word).lower())

    jd_words = _extract_job_words(job_description)
    expected["must"].update(jd_words)

    if target_position:
        for word in re.findall(r"[A-Za-z+#.]{2,}|[\u4e00-\u9fa5]{2,}", target_position):
            expected["must"].add(word.lower())

    has_target = bool(target_position.strip() or job_description.strip())
    if not has_target and target_source == "generic":
        return {
            "score": 50,
            "target_position": "",
            "target_source": "generic",
            "profile": profile_name,
            "matched_keywords": [],
            "missing_keywords": [],
            "focus_suggestions": list(profile["focus"]) if profile else [],
            "evidence_snippets": [],
            "confidence": 0.35,
            "summary": "未提供目标岗位或 JD，岗位匹配仅作通用参考；填写岗位后可获得精准关键词对比。",
        }

    if not expected["must"] and not expected["nice"]:
        for word in keywords[:12]:
            expected["nice"].add(word.lower())

    matched, missing = _match_keywords(resume, expected)
    all_expected = sorted(expected["must"] | expected["nice"])
    if not all_expected:
        return {
            "score": 50,
            "target_position": target_position,
            "target_source": target_source,
            "profile": profile_name,
            "matched_keywords": [],
            "missing_keywords": [],
            "focus_suggestions": [],
            "evidence_snippets": [],
            "confidence": 0.4,
            "match_rate": 0,
            "summary": "暂无可比对的关键词集合，请补充目标岗位或 JD。",
        }

    must_matched = [w for w in sorted(expected["must"]) if w in matched]
    must_missing = [w for w in sorted(expected["must"]) if w in missing]
    ratio = len(matched) / max(len(all_expected), 1)
    match_rate = round(ratio * 100)
    score = round(min(100, max(30, ratio * 100)))
    if must_matched:
        score = min(100, score + min(8, len(must_matched) * 2))
    if must_missing:
        score = max(30, score - min(12, len(must_missing) * 3))
    if profile and matched:
        score = min(100, score + 4)

    source_label = {"manual": "手动输入岗位", "detected": "简历识别岗位", "generic": "通用规则"}[target_source]
    evidence_snippets = _collect_evidence_snippets(text, matched[:8])
    confidence = round(min(0.95, 0.4 + len(matched) / max(len(all_expected), 1) * 0.55), 2)
    return {
        "score": score,
        "target_position": target_position,
        "target_source": target_source,
        "profile": profile_name,
        "matched_keywords": matched[:15],
        "missing_keywords": missing[:12],
        "focus_suggestions": list(profile["focus"]) if profile else [],
        "evidence_snippets": evidence_snippets,
        "confidence": confidence,
        "match_rate": match_rate,
        "summary": (
            f"{source_label}：{target_position or '未识别'}。"
            f"关键词覆盖率 {match_rate}%（已匹配 {len(matched)}/{len(all_expected)}）。"
            + (f" 核心缺口：{'、'.join(must_missing[:4])}。" if must_missing else "")
        ),
    }


def _match_keywords(resume_lower: str, expected: dict[str, set[str]]) -> tuple[list[str], list[str]]:
    matched: list[str] = []
    missing: list[str] = []
    for tier in ("must", "nice"):
        for word in sorted(expected[tier]):
            variants = expand_keyword_variants(word)
            if any(resume_contains_keyword(resume_lower, variant) for variant in variants):
                if word not in matched:
                    matched.append(word)
            elif word not in matched and word not in missing:
                missing.append(word)
    return matched, missing


def _collect_evidence_snippets(text: str, keywords: list[str]) -> list[dict[str, str]]:
    candidates: list[tuple[float, str, str]] = []
    for line in text.splitlines():
        normalized = line.strip()
        if len(normalized) < 8:
            continue
        line_lower = normalized.lower()
        hit_keywords = [keyword for keyword in keywords if resume_contains_keyword(line_lower, keyword)]
        if not hit_keywords:
            continue
        relevance = len(hit_keywords) * 2 + min(len(normalized) / 40, 2)
        candidates.append((relevance, hit_keywords[0], normalized[:120]))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [{"keyword": keyword, "text": snippet, "relevance": round(score, 2)} for score, keyword, snippet in candidates[:5]]


def _select_job_profile(source: str) -> tuple[str, dict[str, Any] | None]:
    best_name = ""
    best_profile: dict[str, Any] | None = None
    best_score = 0
    for name, profile in JOB_PROFILES.items():
        score = 0
        for alias in profile["aliases"]:
            alias_lower = alias.lower()
            if alias_lower in source:
                score += len(alias_lower)
        if score > best_score:
            best_score = score
            best_name = name
            best_profile = profile
    return best_name, best_profile


def _extract_job_words(job_description: str) -> set[str]:
    words = set(word.lower() for word in re.findall(r"[A-Za-z+#.]{2,}|[\u4e00-\u9fa5]{2,}", job_description))
    stopwords = {
        "岗位", "职责", "要求", "优先", "具备", "相关", "能力", "工作", "负责", "完成", "进行", "以及", "通过",
        "我们", "公司", "经验", "良好", "熟悉", "使用", "协助", "参与", "以上", "本科", "大专",
    }
    return {word for word in words if word not in stopwords and len(word) <= 16}
