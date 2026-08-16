"""结构化信息抽取（借鉴开源简历解析常见三层）。

开源常见做法（ResumeParser / JobBot / CandiSift 等）：
1. Segment：先按标题分块（本项目已有 detect_sections）
2. Extract：块内再拆成「条目级」字段（学校/专业/公司/职务/日期）
3. Canonicalize：技能对照词典/图谱做归一，供匹配与展示

本模块只做规则抽取，不引入 spaCy/LLM，保证离线可演示。
"""

from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache
from typing import Any

from app.core.config import settings


DATE_RE = re.compile(r"(?:20\d{2}|19\d{2})[./年-]?\s*(?:0?[1-9]|1[0-2])?")
METRIC_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|人|次|个|项|篇|条|小时|天|周|月|元|w\+?|W\+?|万|k\+?|K\+?)")
DATE_RANGE_RE = re.compile(
    r"(?:20\d{2}|19\d{2})[./年-]?\s*(?:0?[1-9]|1[0-2])?\s*(?:-|至|~|—|–|到)\s*"
    r"(?:20\d{2}|19\d{2}|今|现在|至今|present)",
    re.I,
)
SCHOOL_TOKEN_RE = re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,30}(?:大学|学院|学校|职业技术学院|职业技术大学))")
DEGREE_RE = re.compile(r"(博士|硕士|研究生|本科|专科|大专|高职)")
MAJOR_RE = re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,24}专业)|专业[:：]\s*([\u4e00-\u9fa5A-Za-z]{2,24})")
ORG_TOKEN_RE = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9（）()]{2,40}(?:公司|集团|有限公司|股份公司|工作室|中心|传媒|科技|网络|医院|学校|学院))"
)
ROLE_TOKEN_RE = re.compile(
    r"(?:任|担任|任职)?([\u4e00-\u9fa5A-Za-z]{2,16}(?:干事|部长|委员|助理|实习生|专员|运营|设计师|工程师|经理|成员|负责人))"
)
YEAR_RE = re.compile(r"(20\d{2}|19\d{2})")


def extract_structured_profile(sections: dict[str, list[str]], text: str = "") -> dict[str, Any]:
    """从分节结果抽取条目级结构。"""
    from app.services.score_engine import classify_resume_line

    education = [_parse_education_line(line) for line in sections.get("education") or []]
    education = [item for item in education if item]

    experience: list[dict[str, Any]] = []
    for key in ("internship", "projects", "campus"):
        experience.extend(_parse_experience_block(key, sections.get(key) or []))

    awards = [_parse_award_line(line) for line in sections.get("awards") or []]
    # 校园块里的获奖行也收进来
    for line in sections.get("campus") or []:
        if classify_resume_line(line) == "award":
            parsed = _parse_award_line(line)
            if parsed:
                awards.append(parsed)
    awards = _dedupe_by_raw(awards)

    for item in education:
        _attach_tenure(item)
    for item in experience:
        _attach_tenure(item)

    skills = extract_canonical_skills(sections, text)
    skills = _tag_implicit_skills(skills, sections)
    total_months = _sum_experience_months(experience)
    return {
        "schema": "resume_structured_v1",
        "source": "rule_segment_extract_canonicalize",
        "education": education,
        "experience": experience,
        "awards": awards,
        "skills": skills,
        "stats": {
            "education_count": len(education),
            "experience_count": len(experience),
            "award_count": len(awards),
            "skill_count": len(skills),
            "implicit_skill_count": len([s for s in skills if s.get("source") == "implicit"]),
            "experience_months": total_months,
            "experience_years": round(total_months / 12.0, 2) if total_months else 0.0,
            "avg_confidence": _avg_confidence(education + experience + awards + skills),
        },
    }


def extract_canonical_skills(sections: dict[str, list[str]], text: str = "") -> list[dict[str, Any]]:
    """技能归一：图谱别名 + 同义词表 + 技能区切词（含经历隐式技能，借鉴 resumeX）。"""
    lexicon = _load_skill_lexicon()
    skills_blob = "\n".join(str(line) for line in (sections.get("skills") or [])).lower()
    experience_blob = "\n".join(
        str(line)
        for key in ("projects", "internship", "campus")
        for line in (sections.get(key) or [])
    ).lower()
    haystacks: list[str] = []
    for key in ("skills", "projects", "internship", "campus", "summary"):
        haystacks.extend(str(line) for line in (sections.get(key) or []))
    if text:
        haystacks.append(text[:4000])
    blob = "\n".join(haystacks)
    lowered = blob.lower()

    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for canonical, aliases in lexicon:
        matched_alias = ""
        for alias in aliases:
            alias_l = alias.lower()
            if len(alias_l) >= 2 and alias_l in lowered:
                matched_alias = alias
                break
        if not matched_alias:
            continue
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        in_skills = any(a.lower() in skills_blob for a in aliases if len(a) >= 2)
        in_exp = any(a.lower() in experience_blob for a in aliases if len(a) >= 2)
        source = "lexicon"
        if in_exp and not in_skills:
            source = "implicit"
        elif in_skills:
            source = "skills_section"
        hits.append(
            {
                "name": canonical,
                "raw": matched_alias,
                "canonical": canonical,
                "confidence": 0.9 if matched_alias.lower() == key else (0.72 if source == "implicit" else 0.78),
                "source": source,
            }
        )

    # 技能区未命中词典的短词也保留（不编造）
    for line in sections.get("skills") or []:
        for token in re.split(r"[、,，/;|｜\s]+", str(line)):
            token = token.strip(" ：:·•-")
            if not (2 <= len(token) <= 20):
                continue
            if re.search(r"(特长|技能|掌握|熟悉|精通|了解)", token):
                continue
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                {
                    "name": token,
                    "raw": token,
                    "canonical": token,
                    "confidence": 0.55,
                    "source": "skills_section",
                }
            )
    return hits[:40]


def parse_date_token(value: str, *, end: bool = False) -> date | None:
    """把简历常见日期归一到年月（开源 resumeX / pyresume 思路）。"""
    text = (value or "").strip().lower()
    if not text:
        return None
    if re.search(r"(今|现在|至今|present|current|ongoing)", text):
        return date.today().replace(day=1)
    match = re.search(r"(20\d{2}|19\d{2})\s*[./年\-]?\s*(0?[1-9]|1[0-2])?", text)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2) or (12 if end else 1))
    month = min(max(month, 1), 12)
    return date(year, month, 1)


def parse_date_range_months(raw: str) -> dict[str, Any]:
    """解析区间并返回起止月与持续月数（日期优先，不信口头年数）。"""
    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    range_match = DATE_RANGE_RE.search(text)
    if range_match:
        span = range_match.group(0)
        parts = re.split(r"(?:-|至|~|—|–|到)", span, maxsplit=1)
        start = parse_date_token(parts[0] if parts else "", end=False)
        end = parse_date_token(parts[1] if len(parts) > 1 else "", end=True)
    else:
        single = DATE_RE.search(text)
        start = parse_date_token(single.group(0), end=False) if single else None
        end = start
    months = 0
    if start and end:
        if end < start:
            start, end = end, start
        months = max(0, (end.year - start.year) * 12 + (end.month - start.month) + 1)
    return {
        "start_date": start.isoformat() if start else "",
        "end_date": end.isoformat() if end else "",
        "months": months,
    }


def _attach_tenure(item: dict[str, Any]) -> None:
    tenure = parse_date_range_months(str(item.get("date_range") or item.get("raw") or ""))
    item["start_date"] = tenure["start_date"]
    item["end_date"] = tenure["end_date"]
    item["months"] = tenure["months"]


def _sum_experience_months(experience: list[dict[str, Any]]) -> int:
    """合并重叠/相邻区间后再计月（开源常见 tenure merge）。"""
    intervals: list[tuple[date, date]] = []
    for item in experience:
        start_raw = str(item.get("start_date") or "")
        end_raw = str(item.get("end_date") or "")
        try:
            start = date.fromisoformat(start_raw) if start_raw else None
            end = date.fromisoformat(end_raw) if end_raw else None
        except ValueError:
            start, end = None, None
        if start and end:
            if end < start:
                start, end = end, start
            intervals.append((start, end))
            continue
        months = int(item.get("months") or 0)
        if months > 0:
            # 无绝对日期时退化为独立区间（用假锚点避免互相重叠误并）
            anchor = date(2000, 1, 1)
            fake_start = date(anchor.year + len(intervals), 1, 1)
            month_index = fake_start.month - 1 + months - 1
            fake_end = date(fake_start.year + month_index // 12, month_index % 12 + 1, 1)
            intervals.append((fake_start, fake_end))
    return _merged_interval_months(intervals)


def _merged_interval_months(intervals: list[tuple[date, date]]) -> int:
    if not intervals:
        return 0
    ordered = sorted(intervals, key=lambda pair: (pair[0], pair[1]))
    merged: list[list[date]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        # 重叠或首尾相接（同月/次月）都合并
        contiguous = (start.year - last_end.year) * 12 + (start.month - last_end.month) <= 1
        if start <= last_end or contiguous:
            if end > last_end:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    total = 0
    for start, end in merged:
        total += max(0, (end.year - start.year) * 12 + (end.month - start.month) + 1)
    return total


def _tag_implicit_skills(skills: list[dict[str, Any]], sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    # extract_canonical_skills 已标 source；此处仅保底
    _ = sections
    return skills


def experience_detail_lines(structured: dict[str, Any] | None) -> list[str]:
    """供评分证据使用的职责/项目明细行。"""
    from app.services.score_engine import classify_resume_line

    lines: list[str] = []
    for item in (structured or {}).get("experience") or []:
        if not isinstance(item, dict):
            continue
        for bullet in item.get("bullets") or []:
            text = str(bullet).strip()
            if text:
                lines.append(text)
        summary = str(item.get("summary") or "").strip()
        if summary and summary not in lines:
            # 纯头衔行交给 role_title 逻辑，不直接当职责
            if classify_resume_line(summary) == "duty":
                lines.append(summary)
    return lines


def _parse_education_line(line: str) -> dict[str, Any] | None:
    from app.services.score_engine import classify_resume_line

    text = re.sub(r"\s+", " ", str(line or "")).strip()
    if not text or classify_resume_line(text) not in {"education", "other", "duty"}:
        # duty 兜底：专业名含运营时仍可能被判 duty，但有学校词则收
        if not (SCHOOL_TOKEN_RE.search(text) or DEGREE_RE.search(text) or "就读" in text or "专业" in text):
            return None
    if classify_resume_line(text) in {"award", "skills", "role_title"}:
        return None

    school_match = SCHOOL_TOKEN_RE.search(text)
    degree_match = DEGREE_RE.search(text)
    major = ""
    major_match = MAJOR_RE.search(text)
    if major_match:
        major = next((g for g in major_match.groups() if g), "") or ""
        major = major.replace("专业", "")
    elif school_match:
        after = text[school_match.end() :].strip(" ，,|-")
        after = DEGREE_RE.sub("", after)
        after = DATE_RANGE_RE.sub("", after).strip(" ，,|-")
        if 2 <= len(after) <= 24 and not re.search(r"(负责|参与|奖)", after):
            major = after

    date_range = _first_group(DATE_RANGE_RE, text)
    confidence = 0.55
    if school_match:
        confidence += 0.2
    if degree_match:
        confidence += 0.1
    if major:
        confidence += 0.1
    if date_range:
        confidence += 0.05
    return {
        "raw": text,
        "school": school_match.group(1) if school_match else "",
        "major": major,
        "degree": degree_match.group(1) if degree_match else "",
        "date_range": date_range,
        "confidence": round(min(0.98, confidence), 2),
    }


def _parse_experience_block(section_key: str, lines: list[str]) -> list[dict[str, Any]]:
    from app.services.score_engine import classify_resume_line

    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal current
        if current:
            entries.append(current)
            current = None

    for raw in lines:
        line = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not line:
            continue
        kind = classify_resume_line(line)
        if kind == "award":
            continue
        is_header = bool(
            DATE_RANGE_RE.search(line)
            or DATE_RE.search(line)
            or ROLE_TOKEN_RE.search(line)
            or ORG_TOKEN_RE.search(line)
            or kind == "role_title"
        )
        looks_bullet = kind == "duty" or bool(METRIC_RE.search(line)) or line.startswith(("•", "-", "·", "1.", "2.", "3."))
        if is_header and not (looks_bullet and current and not DATE_RANGE_RE.search(line) and not ROLE_TOKEN_RE.search(line)):
            flush()
            org = _first_group(ORG_TOKEN_RE, line)
            role = _first_group(ROLE_TOKEN_RE, line)
            current = {
                "raw": line,
                "section": section_key,
                "org": org,
                "role": role,
                "date_range": _first_group(DATE_RANGE_RE, line) or _first_group(DATE_RE, line),
                "summary": line,
                "bullets": [],
                "has_metric": bool(METRIC_RE.search(line)),
                "confidence": 0.62 + (0.12 if org or role else 0) + (0.08 if DATE_RANGE_RE.search(line) else 0),
            }
            current["confidence"] = round(min(0.95, current["confidence"]), 2)
            continue
        if current is None:
            current = {
                "raw": line,
                "section": section_key,
                "org": _first_group(ORG_TOKEN_RE, line),
                "role": _first_group(ROLE_TOKEN_RE, line),
                "date_range": _first_group(DATE_RANGE_RE, line),
                "summary": line,
                "bullets": [],
                "has_metric": bool(METRIC_RE.search(line)),
                "confidence": 0.5,
            }
        if looks_bullet or kind == "duty":
            current["bullets"].append(line)
            if METRIC_RE.search(line):
                current["has_metric"] = True
                current["confidence"] = round(min(0.95, float(current["confidence"]) + 0.05), 2)
        elif line != current.get("summary"):
            current["bullets"].append(line)
    flush()
    return entries


def _parse_award_line(line: str) -> dict[str, Any] | None:
    from app.services.score_engine import classify_resume_line

    text = re.sub(r"\s+", " ", str(line or "")).strip()
    if not text:
        return None
    if classify_resume_line(text) not in {"award", "other"} and not re.search(r"(奖|荣誉|称号|先进|十佳)", text):
        return None
    year_match = YEAR_RE.search(text)
    return {
        "raw": text,
        "title": text,
        "year": year_match.group(1) if year_match else "",
        "confidence": 0.8 if year_match else 0.68,
    }


@lru_cache(maxsize=1)
def _load_skill_lexicon() -> tuple[tuple[str, tuple[str, ...]], ...]:
    items: list[tuple[str, tuple[str, ...]]] = []
    # 1) skill graph nodes
    graph_path = settings.data_dir / "skill_graph.json"
    if graph_path.exists():
        try:
            payload = json.loads(graph_path.read_text(encoding="utf-8"))
            for node in payload.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                name = str(node.get("name") or node.get("id") or "").strip()
                if not name:
                    continue
                aliases = [name] + [str(a).strip() for a in (node.get("aliases") or []) if str(a).strip()]
                items.append((name, tuple(dict.fromkeys(aliases))))
        except Exception:
            pass
    # 2) synonym clusters → canonical = cluster key
    syn_path = settings.data_dir / "lexicon" / "skill_synonyms.json"
    if syn_path.exists():
        try:
            payload = json.loads(syn_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for key, values in payload.items():
                    canonical = str(key).strip()
                    if not canonical:
                        continue
                    aliases = [canonical] + [str(v).strip() for v in (values or []) if str(v).strip()]
                    items.append((canonical, tuple(dict.fromkeys(aliases))))
        except Exception:
            pass
    # longer aliases first helps phrase hits when scanning later callers
    items.sort(key=lambda pair: max((len(a) for a in pair[1]), default=0), reverse=True)
    return tuple(items)


def _first_group(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    if match.lastindex:
        for idx in range(1, match.lastindex + 1):
            value = match.group(idx)
            if value:
                return value.strip()
    return match.group(0).strip()


def _dedupe_by_raw(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        # OCR 和复杂模板可能产生空占位项；结构化阶段应丢弃它们，
        # 不能让单个空项阻断整份简历的分析链路。
        if not isinstance(item, dict):
            continue
        key = re.sub(r"\s+", " ", str(item.get("raw") or "")).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _avg_confidence(items: list[dict[str, Any]]) -> float:
    values = [float(item.get("confidence") or 0) for item in items if isinstance(item, dict)]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)
