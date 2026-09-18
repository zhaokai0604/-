"""评分引擎：规则分 + 证据覆盖分。"""

from __future__ import annotations

import re
from typing import Any

WEIGHTS = {
    "content_completeness": 0.20,
    "experience_match": 0.20,
    "language_professionalism": 0.15,
    "format_standardization": 0.10,
    "highlight_strength": 0.15,
    "job_match": 0.20,
}

# 岗位类型权重模板（阶段二：按岗位切换评分权重）
WEIGHT_TEMPLATES: dict[str, dict[str, float]] = {
    "default": dict(WEIGHTS),
    "数据分析": {
        "content_completeness": 0.15,
        "experience_match": 0.20,
        "language_professionalism": 0.10,
        "format_standardization": 0.10,
        "highlight_strength": 0.20,
        "job_match": 0.25,
    },
    "产品经理": {
        "content_completeness": 0.15,
        "experience_match": 0.25,
        "language_professionalism": 0.15,
        "format_standardization": 0.10,
        "highlight_strength": 0.15,
        "job_match": 0.20,
    },
    "前端开发": {
        "content_completeness": 0.10,
        "experience_match": 0.25,
        "language_professionalism": 0.10,
        "format_standardization": 0.10,
        "highlight_strength": 0.15,
        "job_match": 0.30,
    },
    "后端开发": {
        "content_completeness": 0.10,
        "experience_match": 0.25,
        "language_professionalism": 0.10,
        "format_standardization": 0.10,
        "highlight_strength": 0.15,
        "job_match": 0.30,
    },
    "新媒体运营": {
        "content_completeness": 0.15,
        "experience_match": 0.20,
        "language_professionalism": 0.15,
        "format_standardization": 0.10,
        "highlight_strength": 0.25,
        "job_match": 0.15,
    },
}


def resolve_weights(profile_name: str) -> tuple[dict[str, float], str]:
    from app.services.runtime_config import get_score_runtime_config

    runtime = get_score_runtime_config()
    templates: dict[str, dict[str, float]] = {**WEIGHT_TEMPLATES, **(runtime.get("templates") or {})}
    if profile_name and profile_name in templates:
        return templates[profile_name], profile_name
    active = runtime.get("active_template") or "default"
    if active in templates:
        return templates[active], active
    return WEIGHTS, "default"

SECTION_LABELS = {
    "basic_info": "个人信息",
    "education": "教育背景",
    "internship": "实习/工作经历",
    "projects": "项目/实训经历",
    "campus": "校园实践",
    "skills": "技能证书",
    "awards": "荣誉奖项",
    "summary": "自我评价/求职意向",
}

ACTION_WORDS = ["负责", "主导", "参与", "协助", "设计", "开发", "运营", "策划", "优化", "分析", "搭建", "完成", "推进", "落地", "复盘"]
RESULT_WORDS = ["提升", "增长", "降低", "减少", "完成", "达成", "获得", "荣获", "获评", "被评", "排名", "播放", "阅读", "转化", "粉丝", "点赞", "收藏"]
VAGUE_WORDS = ["很多", "比较", "非常", "一些", "各种", "良好", "较强", "熟悉相关", "有一定"]
# 这些行本身不是「职责证据」，不应按「缺量化」打低信噪比
EDUCATION_LINE_RE = re.compile(r"(就读|毕业于|教育背景|大学|学院|专业|本科|专科|大专|硕士|博士|高职|学历|主修)")
AWARD_LINE_RE = re.compile(r"(奖|荣誉|称号|奖学金|十佳|先进|优秀|证书|被评|荣获|获评|表彰)")
SKILL_LINE_RE = re.compile(r"^(特长|技能|专业技能|职业技能|掌握|熟悉|精通|了解)[:：]?")
ROLE_TITLE_RE = re.compile(r"(担任|任职于?|任|就职于).{0,48}(干事|部长|委员|助理|实习生|成员|负责人)")
DOMAIN_SIGNAL_WORDS = [
    "小红书",
    "公众号",
    "抖音",
    "短视频",
    "新媒体",
    "内容运营",
    "淘宝运营",
    "网络整合营销",
    "SEO",
    "SEM",
    "PS",
    "PR",
    "AE",
    "剪映",
    "文案",
    "选题",
    "推广",
    "转化率",
    "完播率",
    "阅读量",
    "播放量",
    "涨粉",
]
METRIC_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|人|次|个|项|篇|条|小时|天|周|月|元|w\+?|W\+?|万|k\+?|K\+?)")
DATE_RE = re.compile(r"(?:20\d{2}|19\d{2})[./年-]?\s*(?:0?[1-9]|1[0-2])?")


def label_for_score(key: str) -> str:
    return {
        "content_completeness": "内容完整性",
        "experience_match": "经历相关性",
        "language_professionalism": "语言专业性",
        "format_standardization": "格式规范性",
        "highlight_strength": "亮点量化程度",
        "job_match": "岗位语义匹配",
    }[key]


def resolve_target_position(
    parsed: dict[str, Any],
    manual_target_position: str,
    *,
    source_override: str | None = None,
    allow_detected: bool = True,
) -> tuple[str, str]:
    if source_override:
        return manual_target_position.strip(), source_override
    manual = manual_target_position.strip()
    if manual:
        return manual, "manual"
    if allow_detected:
        detected = (parsed.get("detected_target_position") or "").strip()
        if detected:
            return detected, "detected"
    return "", "generic"


def build_evidence(
    sections: dict[str, list[str]],
    text: str,
    structured: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    experience_lines = _experience_lines(sections, structured)
    metric_lines = [line for line in experience_lines if METRIC_RE.search(line)]
    action_lines = [line for line in experience_lines if _contains_any(line, ACTION_WORDS)]
    result_lines = [line for line in experience_lines if _contains_any(line, RESULT_WORDS)]
    # 仅对「职责描述」要求可验证产出；教育/特长/获奖/纯头衔不进弱经历
    weak_experience_lines = [
        line for line in experience_lines
        if _is_quantifiable_duty_line(line)
        and 12 <= len(line) <= 110
        and not METRIC_RE.search(line)
        and not _contains_any(line, RESULT_WORDS)
    ][:5]
    role_title_lines = [
        line for line in experience_lines
        if classify_resume_line(line) == "role_title" and 12 <= len(line) <= 120
    ][:3]
    long_lines = [line for line in lines if len(line) > 90][:5]
    vague_lines = [
        line for line in lines
        if _contains_any(line, VAGUE_WORDS) and classify_resume_line(line) not in {"education", "award", "skills"}
    ][:5]
    course_lines = [line for line in lines if _is_course_or_training_line(line)][:5]
    domain_keywords = [word for word in DOMAIN_SIGNAL_WORDS if _contains_any(text, [word])]
    domain_signal_lines = [line for line in lines if _contains_any(line, DOMAIN_SIGNAL_WORDS)][:6]
    low_snr_zones = _build_low_snr_zones(weak_experience_lines, vague_lines, role_title_lines, experience_lines)
    evidence_confidence = _evidence_confidence(
        metric_line_count=len(metric_lines),
        result_line_count=len(result_lines),
        weak_count=len(weak_experience_lines),
        vague_count=len(vague_lines),
        experience_count=len(experience_lines),
    )
    section_counts = {key: len(value) for key, value in sections.items()}
    missing_sections = [key for key in ["basic_info", "education", "internship", "projects", "skills"] if not sections.get(key)]
    return {
        "section_counts": section_counts,
        "missing_sections": missing_sections,
        "experience_line_count": len(experience_lines),
        "metric_line_count": len(metric_lines),
        "action_line_count": len(action_lines),
        "result_line_count": len(result_lines),
        "date_line_count": len([line for line in lines if DATE_RE.search(line)]),
        "long_lines": long_lines,
        "vague_lines": vague_lines,
        "weak_experience_lines": weak_experience_lines,
        "role_title_lines": role_title_lines,
        "sample_metric_lines": metric_lines[:3],
        "sample_action_lines": action_lines[:3],
        "course_lines": course_lines,
        "domain_keywords": domain_keywords[:12],
        "domain_signal_lines": domain_signal_lines,
        "low_snr_zones": low_snr_zones,
        "evidence_confidence": evidence_confidence,
    }


def score_resume(
    parsed: dict[str, Any],
    target_position: str = "",
    job_description: str = "",
    *,
    target_source_override: str | None = None,
    allow_detected: bool = True,
) -> dict[str, Any]:
    from app.services.match_engine import match_job

    text = parsed.get("raw_text", "")
    sections = parsed.get("sections", {})
    keywords = parsed.get("detected_keywords", [])
    parse_quality = parsed.get("parse_quality", "medium")
    parse_warnings = parsed.get("parse_warnings") or parsed.get("warnings", [])
    resolved_target_position, target_source = resolve_target_position(
        parsed,
        target_position,
        source_override=target_source_override,
        allow_detected=allow_detected,
    )
    structured = parsed.get("structured")
    if not isinstance(structured, dict):
        entities = parsed.get("entities") if isinstance(parsed.get("entities"), dict) else {}
        structured = entities.get("structured") if isinstance(entities.get("structured"), dict) else None

    evidence = build_evidence(sections, text, structured if isinstance(structured, dict) else None)
    match_result = match_job(
        text,
        keywords,
        resolved_target_position,
        job_description,
        target_source,
        sections=sections,
        structured=structured if isinstance(structured, dict) else None,
    )
    weights, weight_template = resolve_weights(match_result.get("profile") or "")
    scores = {
        "content_completeness": _score_completeness(sections, evidence, parse_quality),
        "experience_match": _score_experience(sections, evidence, parse_quality),
        "language_professionalism": _score_language(evidence, parse_quality),
        "format_standardization": _score_format(text, sections),
        "highlight_strength": _score_highlights(evidence, parse_quality),
        "job_match": match_result["score"],
    }
    scores, low_snr_penalty = _apply_low_snr_penalty(scores, evidence, match_result)
    total = round(sum(scores[key] * weights[key] for key in weights), 1)
    scores, total, score_reliability = _apply_parse_quality_policy(scores, total, parse_quality)
    layout_complexity = float(parsed.get("layout_complexity") or 0.0)
    evidence_coverage = _evidence_coverage(sections, evidence, match_result, resolved_target_position)
    quality_warnings = list(dict.fromkeys(str(item) for item in parse_warnings if str(item).strip()))
    if layout_complexity >= 3.5 and parse_quality != "low":
        quality_warnings.append("版式复杂但正文已提取，建议人工核验模块边界。")
        if score_reliability == "normal":
            score_reliability = "layout_review"
    if evidence_coverage < 0.5 and score_reliability == "normal":
        score_reliability = "evidence_review"
    return {
        "total_score": total,
        "weight_template": weight_template,
        "weights_used": weights,
        "target_position": resolved_target_position,
        "target_position_source": target_source,
        "parse_quality": parse_quality,
        "parse_warnings": parse_warnings,
        "scores": scores,
        "score_reliability": score_reliability,
        "layout_complexity": layout_complexity,
        "evidence_coverage": evidence_coverage,
        "quality_warnings": quality_warnings,
        "match_result": match_result,
        "evidence": evidence,
        "low_snr_penalty": low_snr_penalty,
        "evidence_confidence": evidence.get("evidence_confidence", 0.5),
        "low_snr_zones": evidence.get("low_snr_zones", []),
        "chart_data": {
            "bar": [{"name": label_for_score(key), "value": value} for key, value in scores.items()],
            "radar": [{"name": label_for_score(key), "value": value} for key, value in scores.items()],
        },
    }


def _evidence_coverage(
    sections: dict[str, list[str]],
    evidence: dict[str, Any],
    match_result: dict[str, Any],
    target_position: str,
) -> float:
    required = ("education", "internship", "projects", "skills")
    section_rate = sum(1 for key in required if sections.get(key)) / len(required)
    if not target_position:
        return round(section_rate, 3)
    match_rate = float(match_result.get("match_rate") or match_result.get("score") or 0.0) / 100.0
    confidence = float(evidence.get("evidence_confidence") or 0.0)
    return round(max(0.0, min(1.0, section_rate * 0.5 + match_rate * 0.3 + confidence * 0.2)), 3)


def _score_completeness(sections: dict[str, list[str]], evidence: dict[str, Any], parse_quality: str) -> int:
    required = ["basic_info", "education", "internship", "projects", "skills"]
    score = 35
    for key in required:
        count = len(sections.get(key, []))
        if count >= 4:
            score += 13
        elif count > 0:
            score += 8
    if sections.get("awards"):
        score += 4
    if sections.get("campus"):
        score += 3
    if parse_quality == "low":
        score = min(score, 52)
    if len(evidence["missing_sections"]) >= 3 and parse_quality != "low":
        score -= 8
    return _clamp(score)


def _score_experience(sections: dict[str, list[str]], evidence: dict[str, Any], parse_quality: str) -> int:
    score = 42
    score += min(evidence["experience_line_count"], 12) * 3
    score += min(evidence["action_line_count"], 6) * 4
    score += min(evidence["metric_line_count"], 5) * 6
    score += min(evidence["result_line_count"], 5) * 4
    if sections.get("internship") and sections.get("projects"):
        score += 6
    if evidence["experience_line_count"] == 0 and parse_quality != "low":
        score -= 12
    if parse_quality == "low":
        score = min(score, 50)
    return _clamp(score)


def _score_language(evidence: dict[str, Any], parse_quality: str) -> int:
    score = 62
    score += min(evidence["action_line_count"], 7) * 4
    score += min(evidence["result_line_count"], 4) * 3
    score -= min(len(evidence["vague_lines"]), 5) * 5
    score -= min(len(evidence["long_lines"]), 5) * 3
    if parse_quality == "low":
        score = min(score, 55)
    return _clamp(score, 35, 100)


def _score_format(text: str, sections: dict[str, list[str]]) -> int:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return 55
    avg_len = sum(len(line) for line in lines) / len(lines)
    section_count = sum(1 for lines_ in sections.values() if lines_)
    score = 78
    if avg_len > 85:
        score -= 12
    if len(lines) < 8:
        score -= 14
    if section_count >= 5:
        score += 8
    if "@" in text or re.search(r"1[3-9]\d{9}", text):
        score += 6
    if DATE_RE.search(text):
        score += 4
    return _clamp(score, 30, 100)


def _score_highlights(evidence: dict[str, Any], parse_quality: str) -> int:
    score = 45
    score += min(evidence["metric_line_count"], 6) * 7
    score += min(evidence["result_line_count"], 5) * 5
    if evidence["sample_metric_lines"]:
        score += 6
    if not evidence["sample_metric_lines"] and parse_quality != "low":
        score -= 8
    if parse_quality == "low":
        score = min(score, 50)
    return _clamp(score)


def _experience_lines(sections: dict[str, list[str]], structured: dict[str, Any] | None = None) -> list[str]:
    lines: list[str] = []
    if structured:
        from app.services.structured_extract import experience_detail_lines

        for line in experience_detail_lines(structured):
            if _is_experience_detail(line) and line not in lines:
                lines.append(line)
    for key in ["internship", "projects", "campus"]:
        for line in sections.get(key, []):
            if _is_experience_detail(line) and line not in lines:
                # 结构化后仍保留原文职责行；纯教育/特长/获奖不再进入
                kind = classify_resume_line(line)
                if kind in {"education", "skills", "award"}:
                    continue
                lines.append(line)
    return lines


def _is_experience_detail(line: str) -> bool:
    line = line.strip()
    if len(line) < 6:
        return False
    if line in {"实习经历", "工作经历", "项目经历", "项目/作品经历", "项目/实训经历", "校园经历"}:
        return False
    if "教育背景" in line and any(token in line for token in ["学院", "大学", "专业", "主修课程"]):
        return False
    if "主修课程" in line and not any(token in line for token in ["负责", "参与", "完成", "项目", "运营"]):
        return False
    return True


def _is_course_or_training_line(line: str) -> bool:
    if re.search(r"(主修课程|课程|实训|专业课|课程设计)", line):
        return True
    return _contains_any(line, ["SEO", "SEM", "小红书", "淘宝运营", "新媒体营销", "网络整合营销", "PS", "PR", "AE"])


def _contains_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def _apply_parse_quality_policy(
    scores: dict[str, int],
    total: float,
    parse_quality: str,
) -> tuple[dict[str, int], float, str]:
    if parse_quality != "low":
        return scores, total, "normal"
    capped = {key: min(value, 62) for key, value in scores.items()}
    capped_total = min(total, 58.0)
    return capped, capped_total, "low_parse_capped"


def classify_resume_line(line: str) -> str:
    """粗分简历行用途，避免「什么都要量化」。"""
    text = (line or "").strip()
    if not text:
        return "other"
    if SKILL_LINE_RE.search(text) or (
        "、" in text and len(text) <= 40 and not _contains_any(text, ACTION_WORDS) and not DATE_RE.search(text)
    ):
        return "skills"
    # 获奖优先于「含学院名」的误判（如：荣获某某学院十佳歌手）
    if AWARD_LINE_RE.search(text) and not re.search(r"(负责|参与|主导|协助)", text):
        return "award"
    if ROLE_TITLE_RE.search(text) and not re.search(r"(负责|参与|主导|协助|完成了|推进)", text):
        return "role_title"
    # 学历行：明确就读/学历词；避免把「在某某学院任职/获奖」当成教育
    if re.search(r"(就读|毕业于|教育背景|主修|学历)", text) or (
        re.search(r"(专业|本科|专科|大专|硕士|博士)", text)
        and re.search(r"(大学|学院|学校)", text)
        and not re.search(r"(担任|任职|任|干事|部长|奖|荣誉|称号)", text)
    ):
        return "education"
    if _contains_any(text, ACTION_WORDS) or re.search(r"(推文|活动|账号|项目|拍摄|剪辑|设计|制作)", text):
        return "duty"
    return "other"


def _is_quantifiable_duty_line(line: str) -> bool:
    kind = classify_resume_line(line)
    return kind == "duty"


def _build_low_snr_zones(
    weak_experience_lines: list[str],
    vague_lines: list[str],
    role_title_lines: list[str],
    experience_lines: list[str],
) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(text: str, reason: str, confidence: float, label: str) -> None:
        key = text.strip()
        if not key or key in seen:
            return
        # 教育 / 特长 / 获奖不进低信噪比清单
        if classify_resume_line(key) in {"education", "skills", "award"}:
            return
        seen.add(key)
        zones.append(
            {
                "text": key,
                "reason": reason,
                "confidence": confidence,
                "label": label,
            }
        )

    for line in weak_experience_lines:
        _add(
            line,
            "实习/项目职责缺少可验证产出（可补数量、周期或结果；勿编造）",
            0.35,
            "待补充区（职责可验证性）",
        )
    for line in role_title_lines:
        _add(
            line,
            "已有职务头衔，建议补 1～2 条具体职责或活动产出，不必硬凑百分比",
            0.48,
            "可增强区（职责细节）",
        )
    for line in vague_lines:
        _add(
            line,
            "含空泛软词，建议改成具体能力/工具/场景，而非一律量化",
            0.4,
            "待补充区（表述空泛）",
        )
    if not zones:
        for sample in experience_lines:
            if classify_resume_line(sample) != "duty":
                continue
            if len(sample) < 40 and not METRIC_RE.search(sample):
                _add(sample, "职责描述偏短，可补充动作与结果（有数据再写数据）", 0.45, "可增强区（职责细节）")
                break
    return zones[:6]


def _evidence_confidence(
    *,
    metric_line_count: int,
    result_line_count: int,
    weak_count: int,
    vague_count: int,
    experience_count: int,
) -> float:
    if experience_count <= 0:
        return 0.4
    strength = min(metric_line_count, 4) * 0.12 + min(result_line_count, 3) * 0.08
    penalty = min(weak_count, 4) * 0.07 + min(vague_count, 3) * 0.05
    return round(max(0.2, min(0.95, 0.55 + strength - penalty)), 2)


def _apply_low_snr_penalty(
    scores: dict[str, int],
    evidence: dict[str, Any],
    match_result: dict[str, Any],
) -> tuple[dict[str, int], dict[str, Any]]:
    """相关性较高但证据置信度低时强制扣分（贴合 HR：宁愿信数据，不信散文）。"""
    updated = dict(scores)
    confidence = float(evidence.get("evidence_confidence") or 0.5)
    low_zones = evidence.get("low_snr_zones") or []
    job_score = int(match_result.get("score") or updated.get("job_match") or 0)
    experience_score = int(updated.get("experience_match") or 0)
    applied = 0
    reasons: list[str] = []

    duty_zones = [
        zone for zone in low_zones
        if "职责可验证" in str(zone.get("label") or "") or "量化" in str(zone.get("reason") or "")
    ]
    # 只有真正的职责弱证据才重扣；头衔/空泛表述轻扣
    if duty_zones and (job_score >= 65 or experience_score >= 65) and confidence < 0.55:
        applied = min(10, 3 + len(duty_zones) * 2)
        updated["experience_match"] = _clamp(experience_score - applied)
        updated["highlight_strength"] = _clamp(int(updated.get("highlight_strength") or 0) - max(2, applied // 2))
        reasons.append(
            f"经历/岗位相关性较高，但职责证据置信度仅 {int(confidence * 100)}%，"
            f"有 {len(duty_zones)} 处职责描述可验证性不足，已扣 {applied} 分。"
            "教育/获奖/特长不要求硬量化；实习与项目优先补真实产出。"
        )
    elif low_zones and confidence < 0.45:
        applied = min(6, max(2, len(duty_zones) * 2))
        updated["highlight_strength"] = _clamp(int(updated.get("highlight_strength") or 0) - applied)
        reasons.append(
            f"检测到 {len(low_zones)} 处可增强描述，亮点分已下调 {applied} 分；"
            "请优先改写空泛软词与职责细节，勿给学历/奖项硬凑数字。"
        )

    return updated, {
        "applied": applied,
        "evidence_confidence": confidence,
        "zone_count": len(low_zones),
        "reasons": reasons,
    }


def _clamp(value: int, low: int = 35, high: int = 100) -> int:
    return max(low, min(high, round(value)))
