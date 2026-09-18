"""Match parsed resumes against the local, verified public job corpus."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.services.pipeline_utils import expand_keyword_variants, resume_contains_keyword

CORPUS_PATH = Path(__file__).resolve().parents[3] / "data" / "job_market" / "public_job_samples.jsonl"
FALLBACK_LABEL = "offline_rules_fallback"
# 有手动岗位时：在岗位语境下检索，阈值可稍低
MIN_MATCH_SCORE = 0.22
# 未选手动岗位时：禁止「只命中 C语言」这类弱信号就套成具体岗位标题
MIN_AUTO_MATCH_SCORE = 0.42
MIN_AUTO_MUST_COVERAGE = 0.5
MIN_AUTO_POSITION_COVERAGE = 0.34
# 采集时写入 must_skills 的占位备注，不是真实技能
_SKILL_PLACEHOLDER_RE = re.compile(
    r"(岗位详情已核验|技能需人工复核|待人工复核|人工结构化|详情页已核验|技能待补充)",
    re.I,
)
_SKILL_LEXICON = (
    "Python", "Java", "Go", "C++", "C语言", "SQL", "Excel", "Office", "Linux", "Windows",
    "Spring", "Spring Boot", "MySQL", "Redis", "Docker", "Vue", "React", "JavaScript",
    "TypeScript", "FastAPI", "Django", "Selenium", "Postman", "JMeter", "Git",
    "数据分析", "数据清洗", "数据可视化", "机器学习", "深度学习", "新媒体运营", "短视频",
    "剪映", "Photoshop", "PS", "Illustrator", "AI", "网络安全", "渗透测试", "漏洞扫描",
    "防火墙", "Web安全", "自动化测试", "功能测试", "性能测试", "硬件测试", "嵌入式",
    "单片机", "PLC", "AutoCAD", "沟通", "客户对接", "需求分析", "接口测试", "黑盒测试",
)
# 单独出现不足以认定岗位方向的泛技能
_WEAK_SOLE_SKILLS = {
    "c",
    "c语言",
    "c++",
    "python",
    "java",
    "excel",
    "word",
    "ppt",
    "office",
    "沟通",
    "学习能力",
    "实习",
    "项目",
    "责任心",
    "团队",
}


@lru_cache(maxsize=1)
def load_verified_jobs() -> tuple[dict[str, Any], ...]:
    """Load only detail-page records; search-result candidates stay out of core matching."""
    if not CORPUS_PATH.exists():
        return ()
    records: list[dict[str, Any]] = []
    with CORPUS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("source_type") != "public_job_page":
                continue
            if item.get("review_status") not in {"single_source_verified", "expert_reviewed"}:
                continue
            if item.get("target_position") and item.get("source_url"):
                records.append(item)
    return tuple(records)


def clear_job_market_cache() -> None:
    load_verified_jobs.cache_clear()


def public_job_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Return reviewable fields without exposing raw scrape data."""
    education = record.get("education") or {}
    experience = record.get("experience") or {}
    must_skills = _normalize_skill_list(record.get("must_skills"), record)
    nice_skills = _normalize_skill_list(record.get("nice_skills"), record, allow_derive=False)
    responsibilities = _normalize_responsibilities(record.get("responsibilities") or [])
    return {
        "id": record.get("id", ""),
        "target_position": record.get("target_position", ""),
        "category": record.get("category", ""),
        "company": record.get("company", ""),
        "city": record.get("city", ""),
        "education": education.get("raw", "") if isinstance(education, dict) else str(education),
        "experience": experience.get("raw", "") if isinstance(experience, dict) else str(experience),
        "must_skills": must_skills,
        "nice_skills": nice_skills,
        "responsibilities": responsibilities,
        "source_type": record.get("source_type", "public_job_page"),
        "review_status": record.get("review_status", "single_source_verified"),
        "source_url": record.get("source_url", ""),
    }


def list_public_jobs() -> list[dict[str, Any]]:
    return [public_job_payload(record) for record in load_verified_jobs()]


def rank_jobs_for_resume(
    resume_text: str,
    sections: dict[str, Any] | None = None,
    requested_position: str = "",
    requested_description: str = "",
    *,
    top_k: int = 5,
    min_score: float = 0.08,
) -> list[dict[str, Any]]:
    """Rank verified jobs for a resume and return Top-K score cards."""
    scored = _score_job_records(resume_text, sections, requested_position, requested_description)
    return _related_jobs_from_scored(scored, top_k=top_k, min_score=min_score)


def _related_jobs_from_scored(
    scored: list[tuple[float, dict[str, Any], list[str], dict[str, Any]]],
    *,
    top_k: int = 5,
    min_score: float = 0.08,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for score, record, matched, explanation in scored:
        if score < min_score and cards:
            break
        if score <= 0 and not matched:
            continue
        cards.append(
            {
                "rank": len(cards) + 1,
                "id": record.get("id", ""),
                "match_score": round(score, 3),
                "match_percent": int(round(min(max(score, 0.0), 1.0) * 100)),
                "target_position": record.get("target_position", ""),
                "category": record.get("category", ""),
                "company": record.get("company", ""),
                "city": record.get("city", ""),
                "matched_keywords": matched[:8],
                "must_coverage": explanation.get("must_coverage", 0),
                "position_coverage": explanation.get("position_coverage", 0),
                "evidence_coverage": explanation.get("evidence_coverage", 0),
                "source_url": record.get("source_url", ""),
            }
        )
        if len(cards) >= top_k:
            break
    return cards


def find_verified_job(
    *,
    job_id: str = "",
    source_url: str = "",
    target_position: str = "",
) -> dict[str, Any] | None:
    """Locate one verified corpus record for post-analysis job selection."""
    job_id = str(job_id or "").strip()
    source_url = str(source_url or "").strip()
    target_position = str(target_position or "").strip()
    if not job_id and not source_url and not target_position:
        return None
    fallback: dict[str, Any] | None = None
    for record in load_verified_jobs():
        if job_id and str(record.get("id") or "") == job_id:
            return record
        if source_url and str(record.get("source_url") or "") == source_url:
            return record
        if target_position and str(record.get("target_position") or "") == target_position:
            if fallback is None:
                fallback = record
    return fallback


def select_job_for_resume(
    resume_text: str,
    sections: dict[str, Any] | None = None,
    requested_position: str = "",
    requested_description: str = "",
) -> dict[str, Any]:
    """Return a verified job match or an explicit fallback explanation.

    A manually supplied JD remains authoritative. When only a position name is
    supplied, the corpus is searched within that position context. With no
    target, never auto-adopt a job — only return related_jobs for the user to pick.
    """
    requested = f"{requested_position} {requested_description}".strip().lower()
    scored = _score_job_records(resume_text, sections, requested_position, requested_description)
    related_jobs = _related_jobs_from_scored(scored, top_k=5, min_score=0.08)

    # 未选手动岗位：只推荐，不自动采用（避免误套岗）
    if not requested:
        top = scored[0] if scored else None
        return {
            "matched": False,
            "fallback_used": True,
            "recommendation_only": True,
            "adopted_as_target": False,
            "source_type": FALLBACK_LABEL,
            "review_status": "not_applicable",
            "match_score": round(top[0], 3) if top else 0.0,
            "matched_keywords": top[2][:12] if top else [],
            "evidence_coverage": top[3]["evidence_coverage"] if top else 0.0,
            "match_explanation": top[3] if top else {},
            "requirement_basis": {},
            "related_jobs": related_jobs,
            "quality_warning": (
                "未选择目标岗位：已按简历给出相似岗位推荐，未自动采用。"
                "可在分析结果中点击推荐岗位，查看该岗专属评价与匹配报告。"
            ),
        }

    threshold = MIN_MATCH_SCORE
    if not scored or scored[0][0] < threshold or not _accept_auto_match(requested, scored[0][2], scored[0][3]):
        basis = _build_requirement_basis(scored[0][1], scored[0][2]) if scored else {}
        return {
            "matched": False,
            "fallback_used": True,
            "recommendation_only": False,
            "adopted_as_target": False,
            "source_type": FALLBACK_LABEL,
            "review_status": "not_applicable",
            "match_score": round(scored[0][0], 3) if scored else 0.0,
            "matched_keywords": scored[0][2][:12] if scored else [],
            "evidence_coverage": scored[0][3]["evidence_coverage"] if scored else 0.0,
            "match_explanation": scored[0][3] if scored else {},
            "requirement_basis": basis,
            "related_jobs": related_jobs,
            "quality_warning": "真实岗位库未达到匹配阈值，已保留手动/检测岗位或使用通用保底规则。",
        }

    score, record, matched, explanation = scored[0]
    requirement_basis = _build_requirement_basis(record, matched)
    return {
        "matched": True,
        "fallback_used": False,
        "recommendation_only": False,
        "adopted_as_target": True,
        "source_type": record.get("source_type", "public_job_page"),
        "review_status": record.get("review_status", "single_source_verified"),
        "match_score": round(score, 3),
        "matched_keywords": matched[:12],
        "evidence_coverage": explanation["evidence_coverage"],
        "match_explanation": explanation,
        "source_url": record.get("source_url", ""),
        "company": record.get("company", ""),
        "city": record.get("city", ""),
        "category": record.get("category", ""),
        "id": record.get("id", ""),
        "target_position": record.get("target_position", ""),
        "job_description": _record_description(record),
        "requirement_basis": requirement_basis,
        "related_jobs": related_jobs,
        "quality_warning": "公开详情页单一来源核验，不能视为多标注黄金岗位。",
    }


def _build_requirement_basis(record: dict[str, Any], matched: list[str]) -> dict[str, Any]:
    """Expose job requirements and resume evidence counts for analysis UI/report."""
    education = record.get("education") or {}
    experience = record.get("experience") or {}
    must_skills = _normalize_skill_list(record.get("must_skills"), record)
    nice_skills = _normalize_skill_list(record.get("nice_skills"), record, allow_derive=False)
    experience_raw = experience.get("raw", "") if isinstance(experience, dict) else str(experience or "")
    resp_blob = " ".join(str(item) for item in (record.get("responsibilities") or []))
    experience_tags = [
        token
        for token in ("项目经验", "实习", "数据可视化", "工作经验", "校园经历")
        if token in resp_blob or token in experience_raw
    ]
    if not experience_tags and experience_raw:
        experience_tags = [experience_raw]
    matched_set = {str(item).lower() for item in matched}
    hit_skills: list[str] = []
    missing_skills: list[str] = []
    for skill in must_skills:
        skill_l = skill.lower()
        if skill_l in matched_set or any(token in skill_l or skill_l in token for token in matched_set):
            hit_skills.append(skill)
        else:
            missing_skills.append(skill)
    return {
        "target_position": record.get("target_position", ""),
        "education": education.get("raw", "") if isinstance(education, dict) else str(education or ""),
        "must_skills": must_skills[:8],
        "nice_skills": nice_skills[:6],
        "experience_requirements": experience_tags[:4],
        "hit_skills": hit_skills[:8],
        "missing_skills": missing_skills[:8],
        "hit_count": len(hit_skills),
        "miss_count": len(missing_skills),
        "matched_keywords": matched[:8],
    }


def _score_job_records(
    resume_text: str,
    sections: dict[str, Any] | None,
    requested_position: str,
    requested_description: str,
) -> list[tuple[float, dict[str, Any], list[str], dict[str, Any]]]:
    resume = str(resume_text or "").lower()
    requested = f"{requested_position} {requested_description}".strip().lower()
    records = load_verified_jobs()
    evidence_text = _section_evidence(sections)
    scored: list[tuple[float, dict[str, Any], list[str], dict[str, Any]]] = []
    for record in records:
        groups = _record_term_groups(record)
        terms = groups["all"]
        if not terms:
            continue
        matched = [term for term in terms if _contains_any(resume, term)]
        must_coverage = _coverage(groups["must"], matched)
        nice_coverage = _coverage(groups["nice"], matched)
        position_coverage = _coverage(groups["position"], matched)
        resume_score = (must_coverage * 0.55) + (nice_coverage * 0.2) + (position_coverage * 0.25)
        section_score = _section_score(matched, evidence_text)
        context_terms = _tokens(requested)
        context_score = (
            len([term for term in terms if any(_contains_any(term, token) for token in context_terms)])
            / max(min(len(context_terms), 8), 1)
            if context_terms
            else 0.0
        )
        score = (
            resume_score * 0.65 + section_score * 0.15 + context_score * 0.2
            if requested
            else resume_score * 0.8 + section_score * 0.2
        )
        if matched or score > 0:
            explanation = {
                "must_coverage": round(must_coverage, 3),
                "nice_coverage": round(nice_coverage, 3),
                "position_coverage": round(position_coverage, 3),
                "evidence_coverage": round(section_score, 3),
                "education_alignment": _education_alignment(resume, record),
                "experience_alignment": _experience_alignment(resume, record),
            }
            scored.append((score, record, matched, explanation))
    scored.sort(key=lambda item: (item[0], len(item[2])), reverse=True)
    return scored


def _record_terms(record: dict[str, Any]) -> list[str]:
    return _record_term_groups(record)["all"]


def _record_term_groups(record: dict[str, Any]) -> dict[str, list[str]]:
    must_skills = _normalize_skill_list(record.get("must_skills"), record)
    nice_skills = _normalize_skill_list(record.get("nice_skills"), record, allow_derive=False)
    raw_groups = {
        "position": [record.get("target_position", ""), record.get("category", "")],
        "must": must_skills,
        "nice": nice_skills,
    }
    groups: dict[str, list[str]] = {}
    for name, values in raw_groups.items():
        terms: list[str] = []
        for value in values:
            for token in _tokens(str(value)):
                if token not in terms and len(token) >= 2:
                    terms.append(token)
        groups[name] = terms
    groups["all"] = list(dict.fromkeys(groups["position"] + groups["must"] + groups["nice"]))[:32]
    return groups


def _accept_auto_match(requested: str, matched: list[str], explanation: dict[str, Any]) -> bool:
    """未选手动岗位时，拒绝「单凭泛技能」的假阳性命中。"""
    if requested:
        return True
    must_coverage = float(explanation.get("must_coverage") or 0)
    position_coverage = float(explanation.get("position_coverage") or 0)
    if position_coverage >= MIN_AUTO_POSITION_COVERAGE and must_coverage >= 0.34:
        return True
    if must_coverage >= MIN_AUTO_MUST_COVERAGE:
        strong = [term for term in matched if term.lower() not in _WEAK_SOLE_SKILLS]
        if len(strong) >= 2 or (len(strong) >= 1 and position_coverage > 0):
            return True
    return False


def _coverage(terms: list[str], matched: list[str]) -> float:
    if not terms:
        return 0.0
    return len([term for term in terms if term in matched]) / len(terms)


def _section_evidence(sections: dict[str, Any] | None) -> dict[str, str]:
    sections = sections if isinstance(sections, dict) else {}
    return {
        str(key).lower(): " ".join(str(item) for item in value) if isinstance(value, list) else str(value or "")
        for key, value in sections.items()
        if not str(key).startswith("_")
    }


def _section_score(matched: list[str], evidence: dict[str, str]) -> float:
    if not matched or not evidence:
        return 0.0
    weights = {"skills": 1.5, "projects": 1.35, "internship": 1.35, "experience": 1.25, "education": 0.8}
    total = 0.0
    hit = 0.0
    for name, text in evidence.items():
        weight = weights.get(name, 1.0)
        total += weight
        if any(_contains_any(text.lower(), term) for term in matched):
            hit += weight
    return hit / total if total else 0.0


def _education_alignment(resume: str, record: dict[str, Any]) -> str:
    raw = str((record.get("education") or {}).get("raw", ""))
    if not raw or "不限" in raw:
        return "not_required"
    if any(token in resume for token in ("硕士", "研究生", "博士")) and "本科" in raw:
        return "meets"
    if "本科" in raw and "本科" in resume:
        return "meets"
    if "大专" in raw and any(token in resume for token in ("大专", "本科", "硕士", "研究生")):
        return "meets"
    return "unknown"


def _experience_alignment(resume: str, record: dict[str, Any]) -> str:
    raw = str((record.get("experience") or {}).get("raw", ""))
    if not raw or "不限" in raw:
        return "not_required"
    if any(token in resume for token in ("实习", "项目", "工作经历", "工作经验", "负责")):
        return "evidence_found"
    return "unknown"


def _record_description(record: dict[str, Any]) -> str:
    must_skills = _normalize_skill_list(record.get("must_skills"), record)
    nice_skills = _normalize_skill_list(record.get("nice_skills"), record, allow_derive=False)
    responsibilities = _normalize_responsibilities(record.get("responsibilities") or [])
    parts = [
        f"岗位类别：{record.get('category', '')}",
        f"学历要求：{record.get('education', {}).get('raw', '')}",
        f"经验要求：{record.get('experience', {}).get('raw', '')}",
        "必备要求：" + "、".join(must_skills),
        "加分要求：" + "、".join(nice_skills),
        "岗位职责：" + "；".join(responsibilities),
    ]
    return "\n".join(part for part in parts if part and not part.endswith("："))


def _is_skill_placeholder(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if _SKILL_PLACEHOLDER_RE.search(text):
        return True
    if text in {"岗位要求", "岗位职责", "岗位内容", "任职要求", "工作职责"}:
        return True
    return False


def _normalize_responsibilities(values: list[Any]) -> list[str]:
    cleaned: list[str] = []
    for item in values:
        text = re.sub(r"\s+", " ", str(item or "")).strip(" \"'“”")
        if not text or _is_skill_placeholder(text):
            continue
        if re.fullmatch(r"(岗位职责|岗位要求|任职要求|工作职责|岗位内容)\s*[:：]?", text):
            continue
        cleaned.append(text[:180])
    return cleaned[:12]


def _normalize_skill_list(values: Any, record: dict[str, Any], *, allow_derive: bool = True) -> list[str]:
    raw = values if isinstance(values, list) else []
    cleaned: list[str] = []
    for item in raw:
        text = re.sub(r"\s+", " ", str(item or "")).strip()
        if not text or _is_skill_placeholder(text):
            continue
        if text not in cleaned:
            cleaned.append(text)
    if cleaned or not allow_derive:
        return cleaned[:12]
    return _derive_skills_from_record(record)[:12]


def _derive_skills_from_record(record: dict[str, Any]) -> list[str]:
    blob = "\n".join(
        [
            str(record.get("target_position") or ""),
            str(record.get("category") or ""),
            "\n".join(str(item) for item in (record.get("responsibilities") or [])),
            str(record.get("source_evidence") or ""),
        ]
    )
    found: list[str] = []
    lowered = blob.lower()
    for term in _SKILL_LEXICON:
        if term.lower() in lowered and term not in found:
            found.append(term)
    for match in re.finditer(r"(?:熟悉|掌握|具备|了解|精通|熟练使用)([^，。；;\n]{2,28})", blob):
        phrase = match.group(1).strip(" ：:的、和与")
        phrase = re.split(r"[/、，,]", phrase)[0].strip()
        if not phrase or _is_skill_placeholder(phrase) or len(phrase) < 2:
            continue
        if phrase not in found:
            found.append(phrase[:24])
    return found[:12]


def _contains_any(text: str, term: str) -> bool:
    variants = expand_keyword_variants(term)
    return any(resume_contains_keyword(text, variant) for variant in variants)


def _tokens(value: str) -> list[str]:
    value = str(value or "").lower()
    tokens = re.findall(r"[a-z][a-z0-9+#.-]{1,}|[\u4e00-\u9fa5]{2,}", value)
    return list(dict.fromkeys(token for token in tokens if token not in {"岗位", "职责", "要求", "经验", "学历"}))
