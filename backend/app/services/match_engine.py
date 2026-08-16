"""岗位匹配引擎：关键词检索 + 语义相似度融合 + 岗位画像。"""

from __future__ import annotations

import os
import re
from typing import Any

from app.services.pipeline_utils import expand_keyword_variants, resume_contains_keyword
from app.services.score_engine import JOB_PROFILES
from app.services.semantic_match import semantic_similarity


def match_job(
    text: str,
    keywords: list[str],
    target_position: str,
    job_description: str,
    target_source: str,
    *,
    sections: dict[str, Any] | None = None,
    structured: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = f"{target_position}\n{job_description}".lower()
    resume = text.lower()
    profile_name, profile = _select_job_profile(source)
    expected: dict[str, set[str]] = {"must": set(), "nice": set()}

    if profile:
        for word in profile["keywords"]:
            expected["must"].add(word.lower())

    jd_must, jd_nice = _extract_job_words(job_description)
    expected["must"].update(jd_must)
    expected["nice"].update(jd_nice)

    if target_position:
        known_terms = set(_JD_DOMAIN_TERMS)
        for profile_item in JOB_PROFILES.values():
            known_terms.update(str(word).lower() for word in profile_item.get("keywords", []))
        for word in re.findall(r"[A-Za-z+#.]{2,}|[\u4e00-\u9fa5]{2,}", target_position):
            token = word.lower()
            # 岗位名称本身不是缺失技能；只有其中明确出现的技术/领域词才参与匹配。
            if re.fullmatch(r"[a-z0-9+#.]{2,}", token) or token in known_terms:
                expected["must"].add(token)

    has_target = bool(target_position.strip() or job_description.strip())
    empty_ats = {
        "keyword_match": 50,
        "skills_coverage": 50,
        "section_completeness": _section_completeness(sections),
        "overall": 50,
        "weights": {"keyword_match": 0.55, "skills_coverage": 0.25, "section_completeness": 0.20},
    }
    if not has_target and target_source == "generic":
        return {
            "score": 50,
            "rule_score": 50,
            "semantic_score": 0,
            "target_position": "",
            "target_source": "generic",
            "profile": profile_name,
            "matched_keywords": [],
            "missing_keywords": [],
            "critical_gaps": [],
            "minor_gaps": [],
            "focus_suggestions": list(profile["focus"]) if profile else [],
            "evidence_snippets": [],
            "confidence": 0.35,
            "match_backend": "rules_only",
            "ats_breakdown": empty_ats,
            "summary": "未提供目标岗位或 JD，岗位匹配仅作通用参考；填写岗位后可获得精准关键词对比。",
        }

    if not expected["must"] and not expected["nice"]:
        for word in keywords[:12]:
            expected["nice"].add(word.lower())

    matched, missing, hit_sections = _match_keywords(resume, expected, sections=sections)
    all_expected = sorted(expected["must"] | expected["nice"])
    if not all_expected:
        return {
            "score": 50,
            "rule_score": 50,
            "semantic_score": 0,
            "target_position": target_position,
            "target_source": target_source,
            "profile": profile_name,
            "matched_keywords": [],
            "missing_keywords": [],
            "critical_gaps": [],
            "minor_gaps": [],
            "focus_suggestions": [],
            "evidence_snippets": [],
            "confidence": 0.4,
            "match_rate": 0,
            "match_backend": "rules_only",
            "ats_breakdown": empty_ats,
            "summary": "暂无可比对的关键词集合，请补充目标岗位或 JD。",
        }

    must_matched = [w for w in sorted(expected["must"]) if w in matched]
    must_missing = [w for w in sorted(expected["must"]) if w in missing]
    nice_missing = [w for w in sorted(expected["nice"]) if w in missing]
    ratio = len(matched) / max(len(all_expected), 1)
    match_rate = round(ratio * 100)
    rule_score = round(min(100, max(30, ratio * 100)))
    if must_matched:
        rule_score = min(100, rule_score + min(8, len(must_matched) * 2))
    if must_missing:
        rule_score = max(30, rule_score - min(12, len(must_missing) * 3))
    if profile and matched:
        rule_score = min(100, rule_score + 4)
    # 分节加权：技能/项目命中加分；仅基本信息命中降权
    strong_hits = sum(1 for secs in hit_sections.values() if secs & {"skills", "projects", "internship"})
    weak_only = sum(1 for word, secs in hit_sections.items() if secs and not (secs & {"skills", "projects", "internship", "campus"}))
    if strong_hits:
        rule_score = min(100, rule_score + min(6, strong_hits))
    if weak_only and weak_only >= max(1, len(matched) // 2):
        rule_score = max(30, rule_score - min(8, weak_only * 2))

    hard_constraints = _check_hard_constraints(
        job_description,
        sections=sections,
        structured=structured,
    )
    hard_blocked = any(item.get("status") == "fail" for item in hard_constraints)

    job_text = f"{target_position}\n{job_description}".strip()
    semantic = {"score": 0.0, "confidence": 0.0, "backend": "disabled", "available": False, "summary": ""}
    if _semantic_enabled() and not hard_blocked:
        semantic = semantic_similarity(text, job_text)
    # 规则层负责硬约束、证据和解释；正常排序只使用语义分，避免低质量
    # 规则分通过加权平均污染语义排序。语义不可用时才回退规则分。
    if hard_blocked:
        score = 0
        match_backend = "rules_blocked"
        score_policy = "hard_constraint_block"
    elif semantic.get("available"):
        score = int(round(float(semantic.get("score") or 0)))
        match_backend = f"semantic_primary:{semantic.get('backend')}"
        score_policy = "semantic_primary_rule_evidence"
    else:
        score = int(rule_score)
        match_backend = "rules_fallback"
        score_policy = "rule_fallback"

    ats_breakdown = _build_ats_breakdown(
        keyword_ratio=ratio,
        must_total=len(expected["must"]),
        must_matched_count=len(must_matched),
        sections=sections,
        structured=structured,
        resume_lower=resume,
        must_keywords=sorted(expected["must"]),
    )

    source_label = {
        "manual": "手动输入岗位",
        "detected": "简历识别岗位",
        "selected": "点选推荐岗位",
        "generic": "通用规则",
    }.get(target_source, "通用规则")
    evidence_snippets = _collect_evidence_snippets(text, matched[:8], sections=sections)
    rule_confidence = round(min(0.95, 0.4 + len(matched) / max(len(all_expected), 1) * 0.55), 2)
    confidence = (
        float(semantic.get("confidence") or 0)
        if semantic.get("available")
        else rule_confidence
    )
    summary = (
        f"{source_label}：{target_position or '未识别'}。"
        f"关键词覆盖率 {match_rate}%（已匹配 {len(matched)}/{len(all_expected)}）。"
        + (
            f" 语义主分 {round(float(semantic.get('score') or 0))}，规则层仅提供证据与缺口。"
            if semantic.get("available")
            else " 语义模型不可用，已回退规则分。"
        )
        + (" 学历等硬约束未通过，已拦截语义排序。" if hard_blocked else "")
        + (f" 核心缺口：{'、'.join(must_missing[:4])}。" if must_missing else "")
        + f" ATS分项 {ats_breakdown['overall']}。"
    )
    return {
        "score": score,
        "rule_score": round(float(rule_score), 1),
        "semantic_score": round(float(semantic.get("score") or 0), 1) if semantic.get("available") else 0,
        "fuse_alpha": 0.0 if semantic.get("available") else 1.0,
        "target_position": target_position,
        "target_source": target_source,
        "profile": profile_name,
        "matched_keywords": matched[:15],
        "missing_keywords": missing[:12],
        "critical_gaps": must_missing[:8],
        "minor_gaps": nice_missing[:8],
        "focus_suggestions": list(profile["focus"]) if profile else [],
        "evidence_snippets": evidence_snippets,
        "confidence": confidence,
        "match_rate": match_rate,
        "match_backend": match_backend,
        "score_policy": score_policy,
        "hard_constraints": hard_constraints,
        "hard_constraint_blocked": hard_blocked,
        "rule_role": "evidence_and_guardrail",
        "ats_breakdown": ats_breakdown,
        "semantic": semantic,
        "summary": summary,
    }


_DEGREE_RANK = {
    "高职": 1,
    "大专": 1,
    "专科": 1,
    "本科": 2,
    "学士": 2,
    "硕士": 3,
    "研究生": 3,
    "博士": 4,
}


def _check_hard_constraints(
    job_description: str,
    *,
    sections: dict[str, Any] | None,
    structured: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return explicit guardrail decisions without changing semantic ranking."""
    jd = str(job_description or "")
    required = [degree for degree in _DEGREE_RANK if degree in jd]
    if not required:
        return []
    required_degree = max(required, key=lambda value: _DEGREE_RANK[value])
    education_text = "\n".join(str(line) for line in (sections or {}).get("education") or [])
    education_text += "\n" + "\n".join(
        str(item.get("raw") or "")
        for item in (structured or {}).get("education") or []
        if isinstance(item, dict)
    )
    observed = [degree for degree in _DEGREE_RANK if degree in education_text]
    if not observed:
        return [{
            "key": "education",
            "required": required_degree,
            "observed": "",
            "status": "unknown",
            "reason": "未识别到明确学历证据，保留语义分析并提示人工核验。",
        }]
    observed_degree = max(observed, key=lambda value: _DEGREE_RANK[value])
    passed = _DEGREE_RANK[observed_degree] >= _DEGREE_RANK[required_degree]
    return [{
        "key": "education",
        "required": required_degree,
        "observed": observed_degree,
        "status": "pass" if passed else "fail",
        "reason": "学历要求满足" if passed else "学历低于岗位硬性要求",
    }]


def _build_ats_breakdown(
    *,
    keyword_ratio: float,
    must_total: int,
    must_matched_count: int,
    sections: dict[str, Any] | None,
    structured: dict[str, Any] | None,
    resume_lower: str,
    must_keywords: list[str],
) -> dict[str, Any]:
    """借鉴 Resume-Matcher ATS：Keyword 55% + Skills 25% + Section 20%。"""
    keyword_match = round(min(100, max(0, keyword_ratio * 100)))
    if must_total > 0:
        skills_coverage = round(100 * must_matched_count / must_total)
    else:
        skills_coverage = keyword_match
    # 结构化技能优先：在技能/隐式技能中再核验 must
    skill_names = {
        str(item.get("canonical") or item.get("name") or "").lower()
        for item in ((structured or {}).get("skills") or [])
        if isinstance(item, dict)
    }
    if skill_names and must_keywords:
        skill_hits = 0
        for word in must_keywords:
            variants = expand_keyword_variants(word)
            if any(resume_contains_keyword(" ".join(skill_names), v) or resume_contains_keyword(resume_lower, v) for v in variants):
                skill_hits += 1
        skills_coverage = round(100 * skill_hits / max(len(must_keywords), 1))
    section_completeness = _section_completeness(sections)
    weights = {"keyword_match": 0.55, "skills_coverage": 0.25, "section_completeness": 0.20}
    overall = round(
        keyword_match * weights["keyword_match"]
        + skills_coverage * weights["skills_coverage"]
        + section_completeness * weights["section_completeness"]
    )
    return {
        "keyword_match": keyword_match,
        "skills_coverage": skills_coverage,
        "section_completeness": section_completeness,
        "overall": overall,
        "weights": weights,
    }


def _section_completeness(sections: dict[str, Any] | None) -> int:
    sections = sections or {}
    checklist = [
        bool(sections.get("education")),
        bool(sections.get("internship") or sections.get("projects") or sections.get("campus")),
        bool(sections.get("skills")),
        bool(sections.get("summary") or sections.get("basic_info")),
    ]
    return round(100 * sum(1 for ok in checklist if ok) / len(checklist))


def _semantic_enabled() -> bool:
    return os.getenv("USE_SEMANTIC_MATCH", "true").lower() == "true"


def _match_keywords(
    resume_lower: str,
    expected: dict[str, set[str]],
    *,
    sections: dict[str, Any] | None = None,
) -> tuple[list[str], list[str], dict[str, set[str]]]:
    matched: list[str] = []
    missing: list[str] = []
    hit_sections: dict[str, set[str]] = {}
    section_blobs = {
        key: "\n".join(str(line) for line in (values or [])).lower()
        for key, values in (sections or {}).items()
        if isinstance(values, list)
    }
    for tier in ("must", "nice"):
        for word in sorted(expected[tier]):
            variants = expand_keyword_variants(word)
            if any(resume_contains_keyword(resume_lower, variant) for variant in variants):
                if word not in matched:
                    matched.append(word)
                secs = {
                    key
                    for key, blob in section_blobs.items()
                    if any(resume_contains_keyword(blob, variant) for variant in variants)
                }
                hit_sections[word] = secs
            elif word not in matched and word not in missing:
                missing.append(word)
    return matched, missing, hit_sections


def _collect_evidence_snippets(
    text: str,
    keywords: list[str],
    *,
    sections: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """优先从分节正文取证（开源常见 source grounding），再回退全文。"""
    from app.services.pipeline_utils import label_for_section

    candidates: list[tuple[float, str, str, str, str]] = []
    section_map = sections if isinstance(sections, dict) else {}
    scanned: set[str] = set()

    def _push(line: str, section_key: str, bonus: float = 0.0) -> None:
        normalized = re.sub(r"\s+", " ", str(line or "")).strip()
        if len(normalized) < 8 or normalized in scanned:
            return
        # 过滤纯联系方式/数字行，避免证据噪声
        if re.fullmatch(r"[\d\s\-+()（）]{8,}", normalized):
            return
        if re.search(r"@", normalized) and len(re.sub(r"[\w.@+\-]", "", normalized)) <= 2 and len(normalized) <= 48:
            return
        scanned.add(normalized)
        line_lower = normalized.lower()
        hit_keywords = [keyword for keyword in keywords if resume_contains_keyword(line_lower, keyword)]
        if not hit_keywords:
            return
        # 经历/技能命中加分，基本信息命中降权
        section_bonus = {
            "skills": 1.2,
            "projects": 1.1,
            "internship": 1.1,
            "campus": 0.6,
            "summary": 0.3,
            "education": 0.2,
            "basic_info": -0.4,
        }.get(section_key, 0.0)
        relevance = len(hit_keywords) * 2 + min(len(normalized) / 40, 2) + section_bonus + bonus
        candidates.append(
            (
                relevance,
                hit_keywords[0],
                normalized[:120],
                section_key,
                label_for_section(section_key) if section_key else "正文",
            )
        )

    preferred = ("skills", "projects", "internship", "campus", "summary", "education", "awards", "basic_info")
    for key in preferred:
        for line in section_map.get(key) or []:
            _push(str(line), key, bonus=0.3)
    if not candidates:
        for line in str(text or "").splitlines():
            _push(line, "", bonus=0.0)

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "keyword": keyword,
            "text": snippet,
            "relevance": round(score, 2),
            "section": section_key,
            "section_label": section_label,
        }
        for score, keyword, snippet, section_key, section_label in candidates[:6]
    ]


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


_JD_STOPWORDS = {
    "岗位", "职责", "要求", "优先", "具备", "相关", "能力", "工作", "负责", "完成", "进行", "以及", "通过",
    "我们", "公司", "经验", "良好", "熟悉", "使用", "协助", "参与", "以上", "本科", "大专", "硕士", "学历",
    "同学", "学生", "团队", "沟通", "积极", "主动", "认真", "负责", "学习", "了解", "掌握", "精通",
    "需要", "可以", "能够", "具有", "拥有", "希望", "欢迎", "加入", "发展", "空间", "待遇", "福利",
    "加班", "双休", "五险", "一金", "薪资", "面议", "城市", "地点", "时间", "实习", "全职", "兼职",
    "内容", "包括", "如下", "等", "及", "与", "和", "或", "的", "了", "等。",
}

# 中文 JD 不做无词典分词：连续中文短语很容易把职责句拆成大量“假关键词”。
# 只有这些岗位领域词，或英文/数字技术词，才进入缺口清单。
_JD_DOMAIN_TERMS = {
    "数据分析", "数据运营", "商业分析", "数据清洗", "数据可视化", "可视化", "机器学习", "深度学习",
    "用户增长", "内容运营", "内容策划", "新媒体运营", "账号运营", "社群运营", "活动策划", "网络推广",
    "品牌营销", "数字营销", "搜索引擎优化", "项目管理", "产品设计", "交互设计", "视觉设计", "平面设计",
    "需求分析", "竞品分析", "用户研究", "原型设计", "接口开发", "系统开发", "前端开发", "后端开发",
    "数据库", "数据建模", "自动化测试", "性能优化", "风险控制", "客户服务", "供应链管理", "电商运营",
    "短视频运营", "视频剪辑", "文案策划", "拍摄剪辑", "直播运营", "用户画像", "指标体系", "报表开发",
}


def _is_skillish_token(token: str) -> bool:
    text = (token or "").strip().lower()
    if not text or text in _JD_STOPWORDS:
        return False
    if re.fullmatch(r"[a-z0-9+#.]{2,}", text):
        return True
    if re.search(r"(python|java|sql|excel|vue|react|数据分析|运营|设计|剪辑|产品|前端|后端|算法|测试|营销)", text):
        return True
    # 过短中文虚词不当 must
    if re.fullmatch(r"[\u4e00-\u9fa5]{2}", text) and text in {
        "分析", "处理", "优化", "管理", "支持", "服务", "业务", "项目", "活动", "方案", "报告", "数据",
    }:
        return False
    return 2 <= len(text) <= 16 and bool(re.search(r"[\u4e00-\u9fa5A-Za-z]", text))


def _extract_job_words(job_description: str) -> tuple[set[str], set[str]]:
    """只抽取可验证的技能/领域词，避免把 JD 普通描述变成虚假缺口。"""
    text = str(job_description or "")
    must: set[str] = set()
    nice: set[str] = set()
    for raw in re.findall(r"[A-Za-z+#.]{2,}", text):
        word = raw.lower()
        if word not in _JD_STOPWORDS and _is_skillish_token(word):
            must.add(word)
    lowered = text.lower()
    known_terms = set(_JD_DOMAIN_TERMS)
    for profile in JOB_PROFILES.values():
        known_terms.update(str(word).lower() for word in profile.get("keywords", []))
    for term in sorted(known_terms, key=lambda value: (-len(value), value)):
        if term in lowered and term not in _JD_STOPWORDS:
            if _is_skillish_token(term):
                must.add(term)
            elif len(term) >= 3:
                nice.add(term)
    # must 过多会稀释匹配，保前 18 个较长词
    if len(must) > 18:
        must = set(sorted(must, key=lambda w: (-len(w), w))[:18])
    return must, nice
