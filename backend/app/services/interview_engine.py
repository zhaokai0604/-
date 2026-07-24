"""基于简历与岗位匹配结果生成面试准备题（离线规则，可选 AI 增强）。"""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.ai_http import post_ai_json
from app.services.pipeline_utils import collect_experience_lines
from app.services.runtime_config import get_ai_runtime_config


def build_interview_prep(
    sections: dict[str, list[str]],
    match_result: dict[str, Any],
    diagnosis: list[str],
    target_position: str = "",
    enable_ai: bool = False,
    evidence: dict[str, Any] | None = None,
    raise_on_ai_failure: bool = False,
) -> dict[str, Any]:
    target_label = target_position or match_result.get("target_position") or "目标岗位"
    categories: list[dict[str, Any]] = []

    intro_questions = [
        {
            "question": f"请用 1 分钟介绍自己，并说明为什么适合「{target_label}」岗位。",
            "tip": "结构：背景 → 核心能力 → 与岗位的匹配点 → 求职动机。",
            "focus": "自我介绍",
        },
        {
            "question": "你认为自己最大的优势是什么？请结合简历中的经历举例说明。",
            "tip": "用 STAR（情境-任务-行动-结果）组织回答。",
            "focus": "自我认知",
        },
    ]
    categories.append({"name": "开场与自我介绍", "questions": intro_questions})

    experience_lines = collect_experience_lines(sections)
    project_questions: list[dict[str, str]] = []
    for line in experience_lines[:3]:
        snippet = re.sub(r"\s+", " ", line).strip()[:60]
        if len(snippet) < 8:
            continue
        project_questions.append(
            {
                "question": f"请详细介绍这段经历：「{snippet}…」。你在其中承担什么角色？取得了什么结果？",
                "tip": "补充量化指标（人数、金额、效率提升等）和具体工具/方法。",
                "focus": "项目深挖",
            }
        )
    for line in experience_lines[3:5]:
        snippet = re.sub(r"\s+", " ", line).strip()
        if len(snippet) < 10 or re.search(r"\d", snippet):
            continue
        project_questions.append(
            {
                "question": f"你提到「{snippet[:50]}…」，请用 STAR 法则说明你的具体贡献与结果。",
                "tip": "补充数字、周期、工具与团队协作细节。",
                "focus": "经历深挖",
            }
        )
    if not project_questions:
        project_questions.append(
            {
                "question": "请分享一段最能体现你专业能力的项目或实习经历。",
                "tip": "若经历较少，可讲课程作业、竞赛或社团项目。",
                "focus": "经历补充",
            }
        )
    weak_lines = (evidence or {}).get("weak_experience_lines") or []
    for line in weak_lines[:2]:
        snippet = re.sub(r"\s+", " ", str(line)).strip()[:50]
        if len(snippet) < 8:
            continue
        project_questions.append(
            {
                "question": f"简历中「{snippet}…」缺少量化结果，请现场补充你做了什么、用了什么方法、取得了什么成果。",
                "tip": "用数字、周期、工具与业务影响说明，避免只描述职责。",
                "focus": "经历补强",
            }
        )
    categories.append({"name": "项目与经历", "questions": project_questions[:6]})

    missing = match_result.get("missing_keywords") or []
    matched = match_result.get("matched_keywords") or []
    role_questions: list[dict[str, str]] = []
    if missing:
        role_questions.append(
            {
                "question": f"岗位要求涉及「{'、'.join(missing[:4])}」等能力，你目前如何补齐或正在学习？",
                "tip": "诚实说明现状，并给出学习计划或相关替代经历。",
                "focus": "能力缺口",
            }
        )
    if matched:
        role_questions.append(
            {
                "question": f"简历中已体现「{'、'.join(matched[:4])}」相关经验，请举例说明你如何运用这些能力解决实际问题。",
                "tip": "把关键词落到具体场景，避免空泛描述。",
                "focus": "优势验证",
            }
        )
    role_questions.append(
        {
            "question": f"你为什么选择「{target_label}」这个方向？未来 3 年有什么规划？",
            "tip": "结合行业认知与个人成长路径，体现稳定性与主动性。",
            "focus": "职业规划",
        }
    )
    categories.append({"name": "岗位匹配", "questions": role_questions[:4]})

    behavior_questions = [
        {
            "question": "请描述一次你遇到挫折或失败的经历，你是如何处理的？",
            "tip": "重点在复盘、改进与后续成果，而非抱怨环境。",
            "focus": "抗压能力",
        },
        {
            "question": "请举例说明你如何与团队成员协作完成一项有挑战的任务。",
            "tip": "突出沟通方式、分工与冲突处理。",
            "focus": "团队协作",
        },
    ]
    for item in diagnosis[:2]:
        behavior_questions.append(
            {
                "question": f"简历诊断提到「{item[:40]}」，如果面试官追问这一点，你会如何回应？",
                "tip": "提前准备改进措施或补充说明，化被动为主动。",
                "focus": "短板应对",
            }
        )
    categories.append({"name": "行为面试", "questions": behavior_questions[:4]})

    skill_lines = _collect_lines(sections, ("skills", "awards", "campus"))
    if skill_lines or missing:
        skill_questions = [
            {
                "question": "请介绍你最熟练的一项专业技能，并说明掌握程度与应用场景。",
                "tip": "区分「了解 / 熟悉 / 精通」，避免夸大。",
                "focus": "技能深度",
            }
        ]
        if missing:
            skill_questions.append(
                {
                    "question": f"若入职后需要快速上手「{missing[0]}」，你的学习路径是什么？",
                    "tip": "可提及文档、课程、实践项目等具体计划。",
                    "focus": "学习能力",
                }
            )
        categories.append({"name": "专业能力", "questions": skill_questions[:3]})

    total = sum(len(cat["questions"]) for cat in categories)
    payload: dict[str, Any] = {
        "summary": f"围绕「{target_label}」生成 {total} 道面试参考题，覆盖自我介绍、经历深挖、岗位匹配与行为面试。",
        "target_position": target_label,
        "question_count": total,
        "categories": categories,
        "mode": "offline",
    }

    if enable_ai:
        enhanced = enhance_interview_prep_with_ai(
            payload,
            sections,
            match_result,
            target_label,
            raise_on_failure=raise_on_ai_failure,
        )
        if enhanced:
            return enhanced
    return payload


def _collect_lines(sections: dict[str, list[str]], keys: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    for key in keys:
        for line in sections.get(key, []) or []:
            text = re.sub(r"\s+", " ", str(line)).strip()
            if text and text not in lines:
                lines.append(text)
    return lines


def enhance_interview_prep_with_ai(
    base: dict[str, Any],
    sections: dict[str, list[str]],
    match_result: dict[str, Any],
    target_label: str,
    *,
    raise_on_failure: bool = False,
) -> dict[str, Any] | None:
    ai_config = get_ai_runtime_config()
    if not ai_config["api_key"]:
        if raise_on_failure:
            raise RuntimeError("未配置 AI API Key，请在管理后台或环境变量中配置后重试。")
        return None

    experience = collect_experience_lines(sections)[:6]
    prompt = (
        "你是高校就业指导老师。请根据简历与岗位匹配信息，生成面试准备题。"
        "只返回 JSON，不要 Markdown。格式："
        '{"categories":[{"name":"分类名","questions":[{"question":"题目","tip":"答题提示","focus":"考察点"}]}]}'
        f"\n目标岗位：{target_label}"
        f"\n缺失关键词：{match_result.get('missing_keywords', [])}"
        f"\n经历摘要：{experience}"
    )
    try:
        response = post_ai_json(
            ai_config["api_url"],
            headers={"Authorization": f"Bearer {ai_config['api_key']}", "Content-Type": "application/json"},
            payload={
                "model": ai_config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 1800,
            },
            timeout=35,
            attempts=2,
        )
        content = response.json()["choices"][0]["message"]["content"]
        cleaned = content.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.S)
        if fence:
            cleaned = fence.group(1).strip()
        data = json.loads(cleaned)
        categories = data.get("categories")
        if not isinstance(categories, list) or not categories:
            if raise_on_failure:
                raise RuntimeError("AI 返回内容缺少可用面试题，请稍后重试。")
            return None
        total = sum(len(cat.get("questions") or []) for cat in categories if isinstance(cat, dict))
        return {
            "summary": f"AI 围绕「{target_label}」生成 {total} 道面试题。",
            "target_position": target_label,
            "question_count": total,
            "categories": categories,
            "mode": "deepseek",
        }
    except Exception as exc:
        if raise_on_failure:
            raise RuntimeError(f"AI 面试题生成失败：{exc}") from exc
        return None


_TIME_LIMIT_BY_CATEGORY = {
    "开场与自我介绍": 90,
    "项目与经历": 180,
    "岗位匹配": 120,
    "行为面试": 150,
    "专业能力": 120,
}


def build_mock_interview_session(interview_prep: dict[str, Any], *, max_steps: int = 5) -> dict[str, Any]:
    """将面试题列表展开为可逐步练习的模拟面试会话（默认精选 5 题）。"""
    all_steps: list[dict[str, Any]] = []
    for category in interview_prep.get("categories") or []:
        if not isinstance(category, dict):
            continue
        name = str(category.get("name") or "综合")
        time_limit = _TIME_LIMIT_BY_CATEGORY.get(name, 120)
        for question in category.get("questions") or []:
            if not isinstance(question, dict):
                continue
            all_steps.append(
                {
                    "step_no": len(all_steps) + 1,
                    "category": name,
                    "question": question.get("question", ""),
                    "tip": question.get("tip", ""),
                    "focus": question.get("focus", ""),
                    "time_limit_sec": time_limit,
                    "rubric": _rubric_for_focus(str(question.get("focus") or "")),
                }
            )

    steps = _pick_mock_steps(all_steps, max_steps)
    for index, step in enumerate(steps):
        step["step_no"] = index + 1

    target = interview_prep.get("target_position") or "目标岗位"
    total_all = len(all_steps)
    summary = f"精选 {len(steps)} 道模拟题（共 {total_all} 道参考题），建议按真实面试节奏逐题作答并自评。"
    return {
        "summary": summary,
        "target_position": target,
        "total_steps": len(steps),
        "total_available": total_all,
        "steps": steps,
    }


def _pick_mock_steps(steps: list[dict[str, Any]], max_steps: int) -> list[dict[str, Any]]:
    if len(steps) <= max_steps:
        return steps
    picked: list[dict[str, Any]] = []
    seen_categories: set[str] = set()
    for step in steps:
        category = step.get("category", "")
        if category in seen_categories:
            continue
        picked.append(step)
        seen_categories.add(category)
        if len(picked) >= max_steps:
            break
    if len(picked) < max_steps:
        for step in steps:
            if step in picked:
                continue
            picked.append(step)
            if len(picked) >= max_steps:
                break
    return picked[:max_steps]


def _rubric_for_focus(focus: str) -> list[str]:
    if "项目" in focus or "经历" in focus:
        return ["是否说明个人角色", "是否有量化结果", "逻辑是否清晰完整"]
    if "岗位" in focus or "能力" in focus or "技能" in focus:
        return ["是否紧扣岗位要求", "是否有具体例证", "表达是否自信得体"]
    if "抗压" in focus or "团队" in focus or "短板" in focus:
        return ["是否真实具体", "是否体现反思与成长", "态度是否积极"]
    return ["表达是否流畅", "内容是否紧扣问题", "是否有说服力"]
