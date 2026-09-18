"""离线简历改写预览：基于 STAR 框架生成可直接参考的成稿表达。"""

from __future__ import annotations

import re
from typing import Any

from app.services.score_engine import ACTION_WORDS, METRIC_RE, VAGUE_WORDS, classify_resume_line

_SECTION_LABELS = {
    "basic_info": "基本信息",
    "education": "教育经历",
    "internship": "实习经历",
    "projects": "项目经历",
    "skills": "技能特长",
    "awards": "荣誉奖项",
    "others": "其他",
}

_ACTION_PREFIX = re.compile(
    r"^(?:负责|主导|参与|协助|完成|进行|开展|承担|从事|执行|配合|支持|实现|搭建|设计|开发|运营|策划|优化|分析|推进|落地|复盘)[：:，,\s]*",
    re.I,
)
_URL_RE = re.compile(r"https?://|www\.|shoturl\.|bit\.ly/|t\.cn/", re.I)
_CONTACT_FIELD_RE = re.compile(
    r"(现居|现居地|居住地|所在地|地址|电话|手机|邮箱|微信|QQ|qq|身高|体重|年龄|民族|籍贯|政治面貌|证件|身份证)",
    re.I,
)
_PORTFOLIO_RE = re.compile(r"(个人作品|作品集|作品链接|作品主页|个人主页|博客|Behance|GitHub|gitee)", re.I)
_SKILLISH_RE = re.compile(
    r"(Python|Java|SQL|Excel|Word|PPT|WPS|Vue|React|PS|PR|AE|Photoshop|Premiere|"
    r"数据分析|可视化|运营|剪辑|设计|开发|测试|Figma|Tableau|Power\s*BI|Office|Canva|剪映)",
    re.I,
)


def _is_skip_rewrite_line(line: str) -> bool:
    """链接、联系方式、作品入口等不应被改写成「编造职责」。"""
    text = re.sub(r"\s+", " ", str(line or "")).strip()
    if not text or len(text) < 4:
        return True
    if _URL_RE.search(text):
        return True
    if _PORTFOLIO_RE.search(text) and (":" in text or "：" in text or _URL_RE.search(text)):
        return True
    if _CONTACT_FIELD_RE.search(text) and not any(token in text for token in ("负责", "参与", "完成", "项目", "实习")):
        return True
    # 纯标签短行
    if re.fullmatch(r"[\u4e00-\u9fa5A-Za-z]{2,8}\s*[:：]?\s*", text):
        return True
    return False


def build_rewrite_preview(
    sections: dict[str, list[str]],
    match_result: dict[str, Any],
    evidence: dict[str, Any],
    target_position: str = "",
) -> dict[str, Any]:
    target_label = target_position or match_result.get("target_position") or "目标岗位"
    missing = [str(k).strip() for k in (match_result.get("missing_keywords") or []) if str(k).strip()]
    matched = [str(k).strip() for k in (match_result.get("matched_keywords") or []) if str(k).strip()]
    tools = _collect_tools(sections, missing, matched)
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_item(section: str, original: str, suggested: str, focus: str) -> None:
        key = re.sub(r"\s+", " ", original.strip())
        if not key or key in seen or not suggested.strip():
            return
        if _is_skip_rewrite_line(key):
            return
        if key == suggested.strip():
            return
        seen.add(key)
        items.append(
            {
                "section": section,
                "original": key,
                "suggested": suggested.strip(),
                "focus": focus,
            }
        )

    for line in evidence.get("sample_metric_lines", [])[:2]:
        if _is_skip_rewrite_line(line):
            continue
        if classify_resume_line(line) in {"education", "skills", "award"}:
            continue
        add_item("经历", line, _lead_with_metric(line, target_label), "结果前置，突出已有数据亮点")

    for line in evidence.get("weak_experience_lines", [])[:4]:
        if _is_skip_rewrite_line(line):
            continue
        if classify_resume_line(line) != "duty":
            continue
        add_item(
            "实习/项目",
            line,
            _rewrite_weak_experience(line, target_label, missing, tools),
            "STAR：背景 → 行动 → 可验证结果（有数据再写，无数据不编）",
        )

    for line in evidence.get("role_title_lines", [])[:2]:
        if _is_skip_rewrite_line(line):
            continue
        add_item(
            "校园/任职",
            line,
            _rewrite_role_title(line, target_label),
            "保留头衔，补具体职责；勿硬凑百分比",
        )

    for line in evidence.get("vague_lines", [])[:3]:
        if _is_skip_rewrite_line(line):
            continue
        if classify_resume_line(line) in {"education", "skills", "award"}:
            continue
        add_item(
            "表达",
            line,
            _rewrite_vague_line(line, tools, missing, target_label),
            "替换空泛软词为具体能力/工具/场景",
        )

    for line in evidence.get("long_lines", [])[:2]:
        if _is_skip_rewrite_line(line):
            continue
        if classify_resume_line(line) in {"education", "award"}:
            continue
        add_item("格式", line, _rewrite_long_line(line, target_label), "长句拆成动作与结果两点")

    keyword_item = _rewrite_missing_keywords(sections, missing, target_label, tools)
    if keyword_item:
        add_item(keyword_item["section"], keyword_item["original"], keyword_item["suggested"], keyword_item["focus"])

    if not items:
        fallback = _fallback_from_sections(sections, target_label, missing, tools)
        for entry in fallback:
            add_item(entry["section"], entry["original"], entry["suggested"], entry["focus"])

    summary = _build_summary(target_label, items, missing, evidence)
    preview = {
        "summary": summary,
        "items": items[:8],
        "target_position": target_label,
        "mode": "offline_star",
    }
    from app.services.optimized_resume import attach_optimized_resume

    return attach_optimized_resume(preview, sections)


def _build_summary(
    target_label: str,
    items: list[dict[str, str]],
    missing: list[str],
    evidence: dict[str, Any],
) -> str:
    if not items:
        return "当前简历表达较完整；如需进一步润色，可开启 AI 深度改写或上传新版本后再次分析。"
    parts = [f"围绕「{target_label}」生成 {len(items)} 条可直接粘贴的成稿参考。"]
    if missing:
        parts.append(f"已尝试融入缺失关键词：{'、'.join(missing[:4])}。")
    if evidence.get("weak_experience_lines"):
        parts.append("实习/项目句可补真实产出；教育、获奖、特长不会强行量化。")
    elif evidence.get("metric_line_count", 0) == 0:
        parts.append("若暂无数据，请写清职责与场景，不要编造数字。")
    return " ".join(parts)


def _collect_tools(
    sections: dict[str, list[str]],
    missing: list[str],
    matched: list[str],
) -> list[str]:
    pool: list[str] = []
    # 只从技能/经历抽工具，避免把「现居地址/身高」当成工具
    source_keys = ("skills", "projects", "internship", "campus")
    for key in source_keys:
        lines = sections.get(key) or []
        if not isinstance(lines, list):
            continue
        for line in lines:
            text = str(line)
            if _is_skip_rewrite_line(text):
                continue
            for token in re.split(r"[、,，/|\s]+", text):
                token = token.strip(" ：:;；")
                if not (2 <= len(token) <= 24):
                    continue
                if _CONTACT_FIELD_RE.search(token) or _URL_RE.search(token):
                    continue
                if not _SKILLISH_RE.search(token) and not re.fullmatch(r"[A-Za-z][A-Za-z0-9+.#]{1,23}", token):
                    continue
                pool.append(token)
    for word in missing + matched:
        cleaned = str(word).strip()
        if not cleaned or _is_skip_rewrite_line(cleaned):
            continue
        if cleaned not in pool:
            pool.append(cleaned)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in pool:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:8]


def _extract_topic(line: str) -> tuple[str, str]:
    text = re.sub(r"\s+", " ", line).strip(" ·•-\t")
    action = "负责"
    match = _ACTION_PREFIX.match(text)
    if match:
        prefix = match.group(0)
        for word in ACTION_WORDS:
            if word in prefix:
                action = word
                break
        text = text[match.end() :].strip("，,；; ")
    topic = text.strip("。；;，,") or "相关业务"
    return action, topic


def _tool_clause(tools: list[str]) -> str:
    cleaned = [t for t in tools if t and not _CONTACT_FIELD_RE.search(t) and not _URL_RE.search(t)]
    if not cleaned:
        return "使用合适工具/方法"
    return f"使用 {'、'.join(cleaned[:3])}"


def _keyword_clause(missing: list[str]) -> str:
    cleaned = [m for m in missing if m and not _CONTACT_FIELD_RE.search(m)][:3]
    if not cleaned:
        return ""
    return f"，覆盖岗位关键词「{'、'.join(cleaned)}」"


def _rewrite_weak_experience(line: str, target: str, missing: list[str], tools: list[str]) -> str:
    action, topic = _extract_topic(line)
    tool_part = _tool_clause(tools)
    kw_part = _keyword_clause(missing)
    if METRIC_RE.search(line):
        return _lead_with_metric(line, target)
    return (
        f"【{target}】{action}{topic}：{tool_part}推进核心任务{kw_part}；"
        f"可补充真实周期/交付物（有数据再写，如完成 __ 项/服务 __ 人，无数据可删占位）"
    )


def _rewrite_role_title(line: str, target: str) -> str:
    text = re.sub(r"\s+", " ", line).strip()
    return (
        f"{text}。主要职责：① 负责 __（宣传/活动/材料）统筹与落地；"
        f"② 完成 __ 场活动或 __ 篇内容产出（请填真实事项，服务「{target}」叙事即可）"
    )


def _lead_with_metric(line: str, target: str) -> str:
    text = re.sub(r"\s+", " ", line).strip()
    match = METRIC_RE.search(text)
    if not match:
        return _rewrite_weak_experience(line, target, [], [])
    metric = match.group(0).strip()
    before = text[: match.start()].strip("，,；; ")
    after = text[match.end() :].strip("，,；; ")
    context = before or after or "核心工作"
    action, topic = _extract_topic(context)
    subject = topic if topic != "相关业务" else context
    tail = after if after and after != subject else ""
    if tail:
        return f"{metric}：{action}{subject}，{tail}（建议保留真实数据并置于句首）"
    return f"{metric}：{action}{subject}，通过可复用方法达成上述结果（建议保留真实数据并置于句首）"


def _rewrite_vague_line(line: str, tools: list[str], missing: list[str], target: str) -> str:
    text = re.sub(r"\s+", " ", line).strip()
    for vague in sorted(VAGUE_WORDS, key=len, reverse=True):
        text = text.replace(vague, "")
    text = re.sub(r"\s+", " ", text).strip("，,。 ")
    tool_part = _tool_clause(tools)
    kw_part = _keyword_clause(missing)
    if re.search(r"工具|技能|技术|软件|WPS|Excel|Office", line, re.I):
        return f"熟练使用 {tool_part.replace('使用 ', '') or 'WPS/Excel'}，可支撑 {target} 场景下的材料整理、数据统计与内容协作{kw_part}"
    return (
        f"具备与 {target} 相关的表达协作与执行能力：在具体场景中{text or '完成专项任务'}，"
        f"可用「场景 + 动作 + 结果」改写，有数据再补充数据"
    )


def _rewrite_long_line(line: str, target: str) -> str:
    text = re.sub(r"\s+", " ", line).strip()
    parts = re.split(r"[；;。]|，(?=\S{8,})", text)
    parts = [part.strip() for part in parts if part.strip()]
    if len(parts) >= 2:
        return f"① {parts[0]}；② {parts[1]}（每条控制在 40 字内，职责写清即可）"
    mid = len(text) // 2
    split_at = text.rfind("，", 0, mid + 20)
    if split_at < 8:
        split_at = mid
    return f"① {text[:split_at].strip()}；② {text[split_at:].strip('，, ')}（拆分为动作与结果两句）"


def _pick_duty_line(sections: dict[str, list[str]], preferred_keys: tuple[str, ...]) -> tuple[str, str] | None:
    for key in preferred_keys:
        for line in sections.get(key) or []:
            text = str(line).strip()
            if _is_skip_rewrite_line(text):
                continue
            kind = classify_resume_line(text)
            if kind in {"education", "award", "skills"}:
                continue
            if kind == "duty" or any(token in text for token in ("负责", "参与", "完成", "协助", "策划", "运营", "开发")):
                return key, text[:120]
    return None


def _rewrite_missing_keywords(
    sections: dict[str, list[str]],
    missing: list[str],
    target: str,
    tools: list[str],
) -> dict[str, str] | None:
    if not missing:
        return None
    # 过滤掉不像技能/岗位词的缺失项（地址碎片等）
    focus_kw = [
        kw
        for kw in missing
        if not _CONTACT_FIELD_RE.search(kw) and not _URL_RE.search(kw) and 1 < len(kw) <= 24
    ][:3]
    if not focus_kw:
        return None
    picked = _pick_duty_line(sections, ("projects", "internship", "campus"))
    if not picked:
        # 没有可改写的职责句时，给出独立补充提示，绝不覆盖作品链接/基本信息
        return {
            "section": "经历补充",
            "original": f"（待补充与「{target}」相关的一条职责描述）",
            "suggested": (
                f"【待补充】围绕「{target}」写一条真实经历，显式体现「{' / '.join(focus_kw)}」；"
                f"有产出再写数字，勿编造。"
            ),
            "focus": "缺失关键词写入新职责句，不覆盖作品链接或联系方式",
        }
    section_key, original = picked
    if _is_skip_rewrite_line(original):
        return None
    tool_part = _tool_clause(tools)
    suggested = (
        f"【{target}】在既有职责基础上补充：{tool_part}完成与「{'/'.join(focus_kw)}」相关的任务，"
        f"并写清真实交付物（有数据再写 __ 份/次，无数据可删占位）"
    )
    return {
        "section": _SECTION_LABELS.get(section_key, "经历"),
        "original": original,
        "suggested": suggested,
        "focus": "把 JD 缺失关键词写入经历句，而非只堆技能栏，更不覆盖链接行",
    }


def _fallback_from_sections(
    sections: dict[str, list[str]],
    target: str,
    missing: list[str],
    tools: list[str],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for key in ("projects", "internship", "skills"):
        lines = sections.get(key) or []
        if not lines:
            continue
        line = str(lines[0]).strip()
        if len(line) < 6 or _is_skip_rewrite_line(line):
            continue
        kind = classify_resume_line(line)
        if kind in {"education", "award", "skills"}:
            continue
        items.append(
            {
                "section": _SECTION_LABELS.get(key, "经历"),
                "original": line[:120],
                "suggested": _rewrite_weak_experience(line, target, missing, tools),
                "focus": "STAR：背景 → 行动 → 可验证结果（有数据再写）",
            }
        )
        if items:
            break
    return items


def enhance_rewrite_with_ai(
    base: dict[str, Any],
    sections: dict[str, list[str]],
    match_result: dict[str, Any],
    target_position: str,
    resume_text: str = "",
    *,
    raise_on_failure: bool = False,
) -> dict[str, Any] | None:
    import json

    from app.services.ai_http import post_ai_json
    from app.services.runtime_config import get_ai_runtime_config

    ai_config = get_ai_runtime_config()
    if not ai_config["api_key"]:
        if raise_on_failure:
            raise RuntimeError("未配置 AI API Key，请在管理后台或环境变量中配置后重试。")
        return None

    target_label = target_position or match_result.get("target_position") or "目标岗位"
    base_items = base.get("items") or []
    originals = [
        item.get("original", "")
        for item in base_items
        if item.get("original") and not re.search(r"https?://|个人作品|现居|身高|邮箱|手机", str(item.get("original")), re.I)
    ]
    if not originals:
        originals = [
            line.strip()
            for key, values in sections.items()
            if isinstance(values, list) and key in {"projects", "internship", "campus"}
            for line in values[:2]
            if str(line).strip() and not re.search(r"https?://|个人作品|现居|身高", str(line), re.I)
        ][:4]
    if not originals:
        if raise_on_failure:
            raise RuntimeError("没有可用于 AI 改写的简历正文，请上传可复制文本的 DOCX 或文字版 PDF。")
        return None

    offline_samples = [
        f"原文：{item.get('original', '')} → 参考：{item.get('suggested', '')}"
        for item in base_items[:4]
        if item.get("original") and item.get("suggested")
    ]

    prompt = (
        "你是高校简历优化专家。请把简历原文改写成可直接粘贴进简历的专业表达。\n"
        "要求：\n"
        "1. 实习/项目职责句优先用 STAR 或「行动 + 方法 + 结果」；\n"
        "2. 必须给出完整改写句，不要只写建议或点评；\n"
        "3. 尽量融入目标岗位与缺失关键词；\n"
        "4. 不要对教育背景、获奖称号、特长清单强行加量化指标；\n"
        "5. 仅当原文是职责/项目描述且缺少结果时，才用 __ 占位提示补数据，严禁编造数字；\n"
        "6. 空泛软词（良好/较强等）改为具体能力、工具或场景；\n"
        "7. 个人作品链接、联系方式、现居/身高体重等基本信息行不要改写或覆盖；\n"
        "8. 严禁把地址、身高、电话等字段拼进经历模板；\n"
        "9. 只返回 JSON，不要 Markdown。\n"
        '格式：{"summary":"一句话总结","items":[{"section":"板块","original":"原文","suggested":"改写","focus":"优化点"}]}\n'
        f"目标岗位：{target_label}\n"
        f"缺失关键词：{match_result.get('missing_keywords', [])}\n"
        f"已匹配关键词：{match_result.get('matched_keywords', [])}\n"
        f"待优化原文：{originals}\n"
    )
    if offline_samples:
        prompt += "离线改写参考（请在此基础上润色，不要简单复述诊断）：\n" + "\n".join(offline_samples) + "\n"
    prompt += f"简历摘要：{resume_text[:3000]}"

    try:
        response = post_ai_json(
            ai_config["api_url"],
            headers={"Authorization": f"Bearer {ai_config['api_key']}", "Content-Type": "application/json"},
            payload={
                "model": ai_config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.35,
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
        items = data.get("items")
        if not isinstance(items, list) or not items:
            if raise_on_failure:
                raise RuntimeError("AI 返回内容缺少可用改写条目，请稍后重试。")
            return None
        normalized: list[dict[str, str]] = []
        for item in items[:8]:
            if not isinstance(item, dict):
                continue
            original = str(item.get("original", "")).strip()
            suggested = str(item.get("suggested", "")).strip()
            if not original or not suggested or original == suggested:
                continue
            normalized.append(
                {
                    "section": str(item.get("section", "经历")),
                    "original": original,
                    "suggested": suggested,
                    "focus": str(item.get("focus", "AI 深度润色")),
                }
            )
        if not normalized:
            if raise_on_failure:
                raise RuntimeError("AI 返回的改写条目不可用，请稍后重试。")
            return None
        from app.services.optimized_resume import attach_optimized_resume

        return attach_optimized_resume(
            {
                "summary": data.get("summary") or f"AI 围绕「{target_label}」生成 {len(normalized)} 条深度改写参考。",
                "items": normalized,
                "target_position": target_label,
                "mode": "deepseek",
            },
            sections,
        )
    except Exception as exc:
        if raise_on_failure:
            raise RuntimeError(f"AI 深度改写失败：{exc}") from exc
        return None
