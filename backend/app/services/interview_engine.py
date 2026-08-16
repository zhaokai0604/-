"""基于简历与岗位匹配结果生成面试准备题（离线规则，可选 AI 增强）。

每次生成会随机抽取不同题面，并尽量避开上一轮已出过的题目。
"""

from __future__ import annotations

import json
import random
import re
import time
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
    *,
    exclude_questions: list[str] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    rng = rng or random.Random()
    round_seed = f"{int(time.time())}-{rng.randint(1000, 9999)}"
    target_label = target_position or match_result.get("target_position") or "目标岗位"
    excluded = {_normalize_question(q) for q in (exclude_questions or []) if str(q).strip()}
    categories: list[dict[str, Any]] = []

    intro_bank = [
        {
            "question": f"请用 1 分钟介绍自己，并说明为什么适合「{target_label}」岗位。",
            "tip": "结构：背景 → 核心能力 → 与岗位的匹配点 → 求职动机。",
            "focus": "自我介绍",
        },
        {
            "question": f"如果只能用三句话向面试官证明你适合「{target_label}」，你会怎么说？",
            "tip": "每句话对应：经历亮点、可迁移能力、对本岗位的理解。",
            "focus": "自我介绍",
        },
        {
            "question": "你认为自己最大的优势是什么？请结合简历中的经历举例说明。",
            "tip": "用 STAR（情境-任务-行动-结果）组织回答。",
            "focus": "自我认知",
        },
        {
            "question": "请用一个具体故事说明你和大多数候选人相比的差异化优势。",
            "tip": "避免空泛形容词，落到工具、方法、结果和可复用经验。",
            "focus": "自我认知",
        },
        {
            "question": f"你最近一次主动了解「{target_label}」岗位或行业信息是什么时候？学到了什么？",
            "tip": "体现信息搜集能力与求职动机，可结合岗位 JD 关键词。",
            "focus": "求职动机",
        },
    ]
    categories.append(
        {
            "name": "开场与自我介绍",
            "questions": _sample_questions(intro_bank, k=2, excluded=excluded, rng=rng),
        }
    )

    experience_lines = list(collect_experience_lines(sections))
    rng.shuffle(experience_lines)
    project_bank: list[dict[str, str]] = []
    for line in experience_lines[:8]:
        snippet = re.sub(r"\s+", " ", line).strip()[:60]
        if len(snippet) < 8:
            continue
        project_bank.extend(_experience_question_variants(snippet))
    weak_lines = list((evidence or {}).get("weak_experience_lines") or [])
    rng.shuffle(weak_lines)
    for line in weak_lines[:3]:
        snippet = re.sub(r"\s+", " ", str(line)).strip()[:50]
        if len(snippet) < 8:
            continue
        project_bank.append(
            {
                "question": f"简历中「{snippet}…」缺少量化结果，请现场补充你做了什么、用了什么方法、取得了什么成果。",
                "tip": "用数字、周期、工具与业务影响说明，避免只描述职责。",
                "focus": "经历补强",
            }
        )
    if not project_bank:
        project_bank = [
            {
                "question": "请分享一段最能体现你专业能力的项目或实习经历。",
                "tip": "若经历较少，可讲课程作业、竞赛或社团项目。",
                "focus": "经历补充",
            },
            {
                "question": "如果让你挑一个最想被追问的项目，你会选哪一个？为什么？",
                "tip": "说明该项目与目标岗位的关联，以及你准备好的量化结果。",
                "focus": "经历补充",
            },
            {
                "question": "请描述一次你从零开始推进任务的经历，你如何拆解目标并交付？",
                "tip": "突出计划、执行、复盘三步，尽量带周期与产出。",
                "focus": "经历补充",
            },
        ]
    categories.append(
        {
            "name": "项目与经历",
            "questions": _sample_questions(project_bank, k=min(4, max(2, len(project_bank))), excluded=excluded, rng=rng),
        }
    )

    missing = list(match_result.get("missing_keywords") or [])
    matched = list(match_result.get("matched_keywords") or [])
    rng.shuffle(missing)
    rng.shuffle(matched)
    role_bank: list[dict[str, str]] = [
        {
            "question": f"你为什么选择「{target_label}」这个方向？未来 1–3 年有什么规划？",
            "tip": "结合行业认知与个人成长路径，体现稳定性与主动性。",
            "focus": "职业规划",
        },
        {
            "question": f"如果同时有两家公司向你发「{target_label}」offer，你会用什么标准做选择？",
            "tip": "可从业务成长、导师机制、岗位职责匹配度等角度回答。",
            "focus": "职业规划",
        },
        {
            "question": f"你理解的「{target_label}」日常工作大概包括哪些内容？你最擅长哪一块？",
            "tip": "先讲岗位认知，再落到自己可验证的经历。",
            "focus": "岗位理解",
        },
    ]
    if missing:
        role_bank.append(
            {
                "question": f"岗位要求涉及「{'、'.join(missing[:4])}」等能力，你目前如何补齐或正在学习？",
                "tip": "诚实说明现状，并给出学习计划或相关替代经历。",
                "focus": "能力缺口",
            }
        )
        role_bank.append(
            {
                "question": f"针对缺失关键词「{missing[0]}」，你能否举一个接近的替代经验证明学习迁移能力？",
                "tip": "强调方法论迁移，而不是硬说已精通。",
                "focus": "能力缺口",
            }
        )
    if matched:
        role_bank.append(
            {
                "question": f"简历中已体现「{'、'.join(matched[:4])}」相关经验，请举例说明你如何运用这些能力解决实际问题。",
                "tip": "把关键词落到具体场景，避免空泛描述。",
                "focus": "优势验证",
            }
        )
        role_bank.append(
            {
                "question": f"如果用「{matched[0]}」这项能力完成一个新任务，你会怎么设计执行步骤？",
                "tip": "给出可落地的步骤清单，体现可迁移性。",
                "focus": "优势验证",
            }
        )
    categories.append(
        {
            "name": "岗位匹配",
            "questions": _sample_questions(role_bank, k=min(3, len(role_bank)), excluded=excluded, rng=rng),
        }
    )

    behavior_bank = [
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
        {
            "question": "讲一次你主动发现问题并推动改进的经历。",
            "tip": "说明问题来源、你的行动、影响范围与结果。",
            "focus": "主动性",
        },
        {
            "question": "当你和上级/同伴意见不一致时，你通常怎么处理？请举一例。",
            "tip": "体现沟通、倾听与基于事实的说服，而非硬刚。",
            "focus": "沟通协作",
        },
        {
            "question": "请分享一次时间紧急、资源有限但仍需交付的经历。",
            "tip": "讲清优先级取舍与最终结果，避免只强调辛苦。",
            "focus": "抗压能力",
        },
    ]
    diagnosis_items = list(diagnosis or [])
    rng.shuffle(diagnosis_items)
    for item in diagnosis_items[:3]:
        text = str(item).strip()
        if len(text) < 6:
            continue
        behavior_bank.append(
            {
                "question": f"简历诊断提到「{text[:40]}」，如果面试官追问这一点，你会如何回应？",
                "tip": "提前准备改进措施或补充说明，化被动为主动。",
                "focus": "短板应对",
            }
        )
    categories.append(
        {
            "name": "行为面试",
            "questions": _sample_questions(behavior_bank, k=min(3, len(behavior_bank)), excluded=excluded, rng=rng),
        }
    )

    skill_lines = _collect_lines(sections, ("skills", "awards", "campus"))
    if skill_lines or missing:
        skill_bank = [
            {
                "question": "请介绍你最熟练的一项专业技能，并说明掌握程度与应用场景。",
                "tip": "区分「了解 / 熟悉 / 精通」，避免夸大。",
                "focus": "技能深度",
            },
            {
                "question": "你最近三个月新学了什么技能？怎么学、怎么验证自己学会了？",
                "tip": "给出学习路径与可展示成果，体现持续学习。",
                "focus": "学习能力",
            },
        ]
        if skill_lines:
            pick = rng.choice(skill_lines)
            snippet = pick[:40]
            skill_bank.append(
                {
                    "question": f"简历里提到「{snippet}」，请说明你实际做到什么程度，以及有哪些可展示作品/结果。",
                    "tip": "用作品、数据或流程说明，避免只报技能名。",
                    "focus": "技能深度",
                }
            )
        if missing:
            skill_bank.append(
                {
                    "question": f"若入职后需要快速上手「{missing[0]}」，你的学习路径是什么？",
                    "tip": "可提及文档、课程、实践项目等具体计划。",
                    "focus": "学习能力",
                }
            )
        categories.append(
            {
                "name": "专业能力",
                "questions": _sample_questions(skill_bank, k=min(2, len(skill_bank)), excluded=excluded, rng=rng),
            }
        )

    total = sum(len(cat["questions"]) for cat in categories)
    payload: dict[str, Any] = {
        "summary": f"本轮围绕「{target_label}」抽取 {total} 道面试训练题（题组 {round_seed[-4:]}），每次重新生成都会换题。",
        "target_position": target_label,
        "question_count": total,
        "categories": categories,
        "mode": "offline",
        "round_id": round_seed,
    }

    if enable_ai:
        enhanced = enhance_interview_prep_with_ai(
            payload,
            sections,
            match_result,
            target_label,
            exclude_questions=list(excluded),
            raise_on_failure=raise_on_ai_failure,
        )
        if enhanced:
            enhanced["round_id"] = round_seed
            return enhanced
    return payload


def _experience_question_variants(snippet: str) -> list[dict[str, str]]:
    return [
        {
            "question": f"请详细介绍这段经历：「{snippet}…」。你在其中承担什么角色？取得了什么结果？",
            "tip": "补充量化指标（人数、金额、效率提升等）和具体工具/方法。",
            "focus": "项目深挖",
        },
        {
            "question": f"围绕「{snippet}…」，如果面试官追问“你个人不可替代的贡献是什么”，你会怎么答？",
            "tip": "区分团队成果与个人动作，强调决策、难点与结果。",
            "focus": "项目深挖",
        },
        {
            "question": f"你提到「{snippet[:50]}…」，请用 STAR 法则说明你的具体贡献与结果。",
            "tip": "补充数字、周期、工具与团队协作细节。",
            "focus": "经历深挖",
        },
        {
            "question": f"回顾「{snippet[:50]}…」，如果重做一次，你会优化哪一步？为什么？",
            "tip": "体现复盘能力，最好给出可验证的改进点。",
            "focus": "经历深挖",
        },
    ]


def _sample_questions(
    bank: list[dict[str, str]],
    *,
    k: int,
    excluded: set[str],
    rng: random.Random,
) -> list[dict[str, str]]:
    if not bank:
        return []
    fresh = [item for item in bank if _normalize_question(item.get("question", "")) not in excluded]
    pool = fresh or list(bank)
    # 同 focus 尽量分散
    rng.shuffle(pool)
    picked: list[dict[str, str]] = []
    seen_focus: set[str] = set()
    seen_q: set[str] = set()
    for item in pool:
        key = _normalize_question(item.get("question", ""))
        if not key or key in seen_q:
            continue
        focus = str(item.get("focus") or "")
        if focus in seen_focus and len(picked) < k:
            # 先尽量覆盖不同考察点，稍后补齐
            continue
        picked.append(item)
        seen_q.add(key)
        if focus:
            seen_focus.add(focus)
        if len(picked) >= k:
            return picked
    for item in pool:
        key = _normalize_question(item.get("question", ""))
        if not key or key in seen_q:
            continue
        picked.append(item)
        seen_q.add(key)
        if len(picked) >= k:
            break
    return picked[:k]


def _normalize_question(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip().lower())


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
    exclude_questions: list[str] | None = None,
    raise_on_failure: bool = False,
) -> dict[str, Any] | None:
    ai_config = get_ai_runtime_config()
    if not ai_config["api_key"]:
        if raise_on_failure:
            raise RuntimeError("未配置 AI API Key，请在管理后台或环境变量中配置后重试。")
        return None

    experience = collect_experience_lines(sections)[:6]
    avoid = [str(q) for q in (exclude_questions or []) if str(q).strip()][:8]
    offline_samples = []
    for category in base.get("categories") or []:
        for item in (category.get("questions") or [])[:2]:
            if item.get("question"):
                offline_samples.append(str(item["question"]))
    prompt = (
        "你是高校就业指导老师。请根据简历与岗位匹配信息，生成一套与以往不同的面试训练题。\n"
        "要求：\n"
        "1. 覆盖开场、经历深挖、岗位匹配、行为面试、专业能力中的至少 4 类；\n"
        "2. 题目必须结合简历经历与目标岗位，避免空泛套话；\n"
        "3. 每题附 tip（答题提示）与 focus（考察点）；\n"
        "4. 本次必须换新角度、新问法，禁止复述「请避免重复的旧题」列表；\n"
        "5. 只返回 JSON，不要 Markdown。\n"
        '格式：{"categories":[{"name":"分类名","questions":[{"question":"题目","tip":"答题提示","focus":"考察点"}]}]}\n'
        f"目标岗位：{target_label}\n"
        f"缺失关键词：{match_result.get('missing_keywords', [])}\n"
        f"已匹配关键词：{match_result.get('matched_keywords', [])}\n"
        f"经历摘要：{experience}\n"
        f"离线候选参考（可改写，勿原样照搬）：{offline_samples[:6]}\n"
    )
    if avoid:
        prompt += f"请避免重复的旧题：{avoid}\n"
    try:
        response = post_ai_json(
            ai_config["api_url"],
            headers={"Authorization": f"Bearer {ai_config['api_key']}", "Content-Type": "application/json"},
            payload={
                "model": ai_config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 2000,
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
            "summary": f"AI 本轮围绕「{target_label}」生成 {total} 道新面试题，建议按模拟面试节奏练习。",
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


def build_mock_interview_session(
    interview_prep: dict[str, Any],
    *,
    max_steps: int = 5,
    exclude_questions: list[str] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """将面试题列表展开为可逐步练习的模拟面试会话（默认随机精选 5 题）。"""
    rng = rng or random.Random()
    excluded = {_normalize_question(q) for q in (exclude_questions or []) if str(q).strip()}
    all_steps: list[dict[str, Any]] = []
    for category in interview_prep.get("categories") or []:
        if not isinstance(category, dict):
            continue
        name = str(category.get("name") or "综合")
        time_limit = _TIME_LIMIT_BY_CATEGORY.get(name, 120)
        for question in category.get("questions") or []:
            if not isinstance(question, dict):
                continue
            text = str(question.get("question") or "").strip()
            if not text:
                continue
            all_steps.append(
                {
                    "step_no": len(all_steps) + 1,
                    "category": name,
                    "question": text,
                    "tip": question.get("tip", ""),
                    "focus": question.get("focus", ""),
                    "time_limit_sec": time_limit,
                    "rubric": _rubric_for_focus(str(question.get("focus") or "")),
                }
            )

    steps = _pick_mock_steps(all_steps, max_steps, excluded=excluded, rng=rng)
    for index, step in enumerate(steps):
        step["step_no"] = index + 1

    target = interview_prep.get("target_position") or "目标岗位"
    round_id = str(interview_prep.get("round_id") or f"mock-{int(time.time())}")
    total_all = len(all_steps)
    summary = (
        f"本轮模拟精选 {len(steps)} 题（题库 {total_all} 道 · 题组 {round_id[-4:]}），"
        f"重新生成会换一套，建议按真实面试节奏作答。"
    )
    return {
        "summary": summary,
        "target_position": target,
        "total_steps": len(steps),
        "total_available": total_all,
        "round_id": round_id,
        "steps": steps,
    }


def _pick_mock_steps(
    steps: list[dict[str, Any]],
    max_steps: int,
    *,
    excluded: set[str],
    rng: random.Random,
) -> list[dict[str, Any]]:
    if not steps:
        return []
    fresh = [step for step in steps if _normalize_question(step.get("question", "")) not in excluded]
    pool = fresh or list(steps)
    rng.shuffle(pool)
    if len(pool) <= max_steps:
        return pool

    # 先按类别各抽 1 题，再随机补齐
    by_category: dict[str, list[dict[str, Any]]] = {}
    for step in pool:
        by_category.setdefault(str(step.get("category") or "综合"), []).append(step)
    categories = list(by_category.keys())
    rng.shuffle(categories)
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category in categories:
        candidates = by_category[category]
        rng.shuffle(candidates)
        for step in candidates:
            key = _normalize_question(step.get("question", ""))
            if key in seen:
                continue
            picked.append(step)
            seen.add(key)
            break
        if len(picked) >= max_steps:
            return picked[:max_steps]
    for step in pool:
        key = _normalize_question(step.get("question", ""))
        if key in seen:
            continue
        picked.append(step)
        seen.add(key)
        if len(picked) >= max_steps:
            break
    return picked[:max_steps]


def _rubric_for_focus(focus: str) -> list[str]:
    if "项目" in focus or "经历" in focus:
        return ["是否说明个人角色", "是否有量化结果", "逻辑是否清晰完整"]
    if "岗位" in focus or "能力" in focus or "技能" in focus:
        return ["是否紧扣岗位要求", "是否有具体例证", "表达是否自信得体"]
    if "抗压" in focus or "团队" in focus or "短板" in focus or "沟通" in focus or "主动" in focus:
        return ["是否真实具体", "是否体现反思与成长", "态度是否积极"]
    return ["表达是否流畅", "内容是否紧扣问题", "是否有说服力"]


def collect_question_texts(payload: dict[str, Any] | None) -> list[str]:
    """从 interview_prep / mock_interview 中提取题干，供下一轮避重。"""
    if not isinstance(payload, dict):
        return []
    texts: list[str] = []
    for category in payload.get("categories") or []:
        if not isinstance(category, dict):
            continue
        for item in category.get("questions") or []:
            if isinstance(item, dict) and item.get("question"):
                texts.append(str(item["question"]))
    for step in payload.get("steps") or []:
        if isinstance(step, dict) and step.get("question"):
            texts.append(str(step["question"]))
    return list(dict.fromkeys(texts))
