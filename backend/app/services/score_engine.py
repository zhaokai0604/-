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

JOB_PROFILES = {
    "数据分析": {
        "aliases": ["数据分析", "数据运营", "商业分析", "数据专员"],
        "keywords": ["python", "sql", "excel", "tableau", "powerbi", "统计", "数据清洗", "可视化", "建模", "指标", "报表"],
        "focus": ["突出数据处理工具", "补充指标口径和分析结论", "用数据量、提升率、转化率证明结果"],
    },
    "产品经理": {
        "aliases": ["产品经理", "产品助理", "产品实习", "产品运营"],
        "keywords": ["需求", "用户", "原型", "竞品", "prd", "axure", "figma", "产品", "沟通", "项目管理", "迭代"],
        "focus": ["说明需求来源", "补充用户痛点和方案取舍", "展示原型、PRD 或上线结果"],
    },
    "前端开发": {
        "aliases": ["前端", "web前端", "前端开发", "前端工程师"],
        "keywords": ["vue", "react", "javascript", "typescript", "html", "css", "组件", "接口", "性能", "响应式"],
        "focus": ["写清技术栈和职责边界", "补充组件、接口、性能优化成果", "提供项目地址或作品截图"],
    },
    "后端开发": {
        "aliases": ["后端", "java开发", "python开发", "后端开发", "服务端"],
        "keywords": ["python", "java", "mysql", "redis", "接口", "fastapi", "spring", "数据库", "缓存", "权限", "部署"],
        "focus": ["说明接口、数据库和部署责任", "补充并发、性能或稳定性指标", "写清业务场景和技术难点"],
    },
    "新媒体运营": {
        "aliases": ["新媒体", "内容运营", "新媒体运营", "运营实习", "小红书运营", "公众号运营"],
        "keywords": ["公众号", "小红书", "抖音", "视频", "剪辑", "文案", "选题", "运营", "账号", "阅读量", "粉丝", "互动"],
        "focus": ["补充账号平台和目标用户", "量化阅读量、播放量、涨粉和互动", "展示选题、文案、排版、复盘能力"],
    },
    "短视频剪辑": {
        "aliases": ["短视频", "剪辑", "视频剪辑", "短视频剪辑师", "后期"],
        "keywords": ["剪辑", "脚本", "拍摄", "pr", "ae", "剪映", "调色", "字幕", "封面", "账号", "播放量", "完播率"],
        "focus": ["说明剪辑软件和制作流程", "补充播放量、完播率、点赞转化", "展示作品链接和个人负责片段"],
    },
    "电商美工": {
        "aliases": ["电商美工", "淘宝美工", "视觉设计", "平面设计"],
        "keywords": ["ps", "photoshop", "详情页", "主图", "海报", "banner", "视觉", "排版", "转化率", "店铺"],
        "focus": ["补充作品类型和设计目标", "量化点击率、转化率或上新数量", "说明工具熟练度和审美风格"],
    },
}

ACTION_WORDS = ["负责", "主导", "参与", "协助", "设计", "开发", "运营", "策划", "优化", "分析", "搭建", "完成", "推进", "落地", "复盘"]
RESULT_WORDS = ["提升", "增长", "降低", "减少", "完成", "达成", "获得", "排名", "播放", "阅读", "转化", "粉丝", "点赞", "收藏"]
VAGUE_WORDS = ["很多", "比较", "非常", "一些", "各种", "良好", "较强", "熟悉相关", "有一定"]
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


def resolve_target_position(parsed: dict[str, Any], manual_target_position: str) -> tuple[str, str]:
    manual = manual_target_position.strip()
    if manual:
        return manual, "manual"
    detected = (parsed.get("detected_target_position") or "").strip()
    if detected:
        return detected, "detected"
    return "", "generic"


def build_evidence(sections: dict[str, list[str]], text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    experience_lines = _experience_lines(sections)
    metric_lines = [line for line in experience_lines if METRIC_RE.search(line)]
    action_lines = [line for line in experience_lines if _contains_any(line, ACTION_WORDS)]
    result_lines = [line for line in experience_lines if _contains_any(line, RESULT_WORDS)]
    weak_experience_lines = [
        line for line in experience_lines
        if 12 <= len(line) <= 110 and not METRIC_RE.search(line) and not _contains_any(line, RESULT_WORDS)
    ][:5]
    long_lines = [line for line in lines if len(line) > 90][:5]
    vague_lines = [line for line in lines if _contains_any(line, VAGUE_WORDS)][:5]
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
        "sample_metric_lines": metric_lines[:3],
        "sample_action_lines": action_lines[:3],
    }


def score_resume(parsed: dict[str, Any], target_position: str = "", job_description: str = "") -> dict[str, Any]:
    from app.services.match_engine import match_job

    text = parsed.get("raw_text", "")
    sections = parsed.get("sections", {})
    keywords = parsed.get("detected_keywords", [])
    parse_quality = parsed.get("parse_quality", "medium")
    parse_warnings = parsed.get("parse_warnings") or parsed.get("warnings", [])
    resolved_target_position, target_source = resolve_target_position(parsed, target_position)

    evidence = build_evidence(sections, text)
    match_result = match_job(text, keywords, resolved_target_position, job_description, target_source)
    scores = {
        "content_completeness": _score_completeness(sections, evidence, parse_quality),
        "experience_match": _score_experience(sections, evidence, parse_quality),
        "language_professionalism": _score_language(evidence, parse_quality),
        "format_standardization": _score_format(text, sections),
        "highlight_strength": _score_highlights(evidence, parse_quality),
        "job_match": match_result["score"],
    }
    total = round(sum(scores[key] * WEIGHTS[key] for key in WEIGHTS), 1)
    return {
        "total_score": total,
        "target_position": resolved_target_position,
        "target_position_source": target_source,
        "parse_quality": parse_quality,
        "parse_warnings": parse_warnings,
        "scores": scores,
        "match_result": match_result,
        "evidence": evidence,
        "chart_data": {
            "bar": [{"name": label_for_score(key), "value": value} for key, value in scores.items()],
            "radar": [{"name": label_for_score(key), "value": value} for key, value in scores.items()],
        },
    }


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
        score = max(score, 55)
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
        score = max(score, 55)
    return _clamp(score)


def _score_language(evidence: dict[str, Any], parse_quality: str) -> int:
    score = 62
    score += min(evidence["action_line_count"], 7) * 4
    score += min(evidence["result_line_count"], 4) * 3
    score -= min(len(evidence["vague_lines"]), 5) * 5
    score -= min(len(evidence["long_lines"]), 5) * 3
    if parse_quality == "low":
        score = max(score, 55)
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
        score = max(score, 55)
    return _clamp(score)


def _experience_lines(sections: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    for key in ["internship", "projects", "campus"]:
        lines.extend(line for line in sections.get(key, []) if _is_experience_detail(line))
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


def _contains_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def _clamp(value: int, low: int = 35, high: int = 100) -> int:
    return max(low, min(high, round(value)))
