"""离线简历改写预览：基于 STAR 框架生成可直接参考的成稿表达。"""

from __future__ import annotations

import re
from typing import Any

from app.services.score_engine import ACTION_WORDS, METRIC_RE, VAGUE_WORDS

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
        add_item("经历", line, _lead_with_metric(line, target_label), "结果前置，突出量化亮点")

    for line in evidence.get("weak_experience_lines", [])[:4]:
        add_item(
            "经历",
            line,
            _rewrite_weak_experience(line, target_label, missing, tools),
            "STAR 结构：背景 → 行动 → 量化结果",
        )

    for line in evidence.get("vague_lines", [])[:3]:
        add_item(
            "表达",
            line,
            _rewrite_vague_line(line, tools, missing, target_label),
            "替换空泛词，补充工具与可验证产出",
        )

    for line in evidence.get("long_lines", [])[:2]:
        add_item("格式", line, _rewrite_long_line(line, target_label), "长句拆分为动作 + 结果两点")

    keyword_item = _rewrite_missing_keywords(sections, missing, target_label, tools)
    if keyword_item:
        add_item(keyword_item["section"], keyword_item["original"], keyword_item["suggested"], keyword_item["focus"])

    if not items:
        fallback = _fallback_from_sections(sections, target_label, missing, tools)
        for entry in fallback:
            add_item(entry["section"], entry["original"], entry["suggested"], entry["focus"])

    summary = _build_summary(target_label, items, missing, evidence)
    return {
        "summary": summary,
        "items": items[:8],
        "target_position": target_label,
        "mode": "offline_star",
    }


def _build_summary(
    target_label: str,
    items: list[dict[str, str]],
    missing: list[str],
    evidence: dict[str, Any],
) -> str:
    if not items:
        return "当前简历表达较完整；如需进一步润色，可开启 AI 深度改写或上传新版本后再次分析。"
    parts = [f"围绕「{target_label}」生成 {len(items)} 条可直接粘贴的成稿参考（STAR / 结果前置）。"]
    if missing:
        parts.append(f"已尝试融入缺失关键词：{'、'.join(missing[:4])}。")
    if evidence.get("metric_line_count", 0) == 0:
        parts.append("原文量化不足，改写句中保留 __ 占位符，请替换为真实数据。")
    return " ".join(parts)


def _collect_tools(
    sections: dict[str, list[str]],
    missing: list[str],
    matched: list[str],
) -> list[str]:
    pool: list[str] = []
    for lines in sections.values():
        if not isinstance(lines, list):
            continue
        for line in lines:
            for token in re.split(r"[、,，/|\s]+", str(line)):
                token = token.strip()
                if 2 <= len(token) <= 24 and re.search(r"[A-Za-z\u4e00-\u9fff]", token):
                    pool.append(token)
    for word in missing + matched:
        if word not in pool:
            pool.append(word)
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
    if not tools:
        return "使用 __工具/方法"
    picked = tools[:3]
    return f"使用 {'、'.join(picked)}"


def _keyword_clause(missing: list[str]) -> str:
    if not missing:
        return ""
    return f"，覆盖岗位关键词「{'、'.join(missing[:3])}」"


def _rewrite_weak_experience(line: str, target: str, missing: list[str], tools: list[str]) -> str:
    action, topic = _extract_topic(line)
    tool_part = _tool_clause(tools)
    kw_part = _keyword_clause(missing)
    if METRIC_RE.search(line):
        return _lead_with_metric(line, target)
    return (
        f"【{target}】{action}{topic}：{tool_part}推进核心任务，"
        f"在 __ 周期内完成 __ 项交付{kw_part}，使 __ 指标提升 __%（请填入真实数据）"
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
    if re.search(r"工具|技能|技术|软件", line):
        return f"{tool_part}完成 {target} 相关任务（如数据处理/方案落地），产出 __ 份成果{kw_part}"
    return f"在 {target} 场景下，{tool_part}完成{text or '专项任务'}，量化产出 __ 项/提升 __%"


def _rewrite_long_line(line: str, target: str) -> str:
    text = re.sub(r"\s+", " ", line).strip()
    parts = re.split(r"[；;。]|，(?=\S{8,})", text)
    parts = [part.strip() for part in parts if part.strip()]
    if len(parts) >= 2:
        return f"① {parts[0]}；② {parts[1]}（每条控制在 40 字内，并补充量化结果）"
    mid = len(text) // 2
    split_at = text.rfind("，", 0, mid + 20)
    if split_at < 8:
        split_at = mid
    return f"① {text[:split_at].strip()}；② {text[split_at:].strip('，, ')}（拆分为动作与结果两句）"


def _rewrite_missing_keywords(
    sections: dict[str, list[str]],
    missing: list[str],
    target: str,
    tools: list[str],
) -> dict[str, str] | None:
    if not missing:
        return None
    focus_kw = missing[:3]
    section_key = "projects" if sections.get("projects") else "internship" if sections.get("internship") else "skills"
    lines = sections.get(section_key) or []
    original = lines[0][:120] if lines else f"（待补充与 {target} 相关的{ _SECTION_LABELS.get(section_key, '经历') }描述）"
    tool_part = _tool_clause(tools)
    suggested = (
        f"【{target}】{tool_part}完成「{'/'.join(focus_kw)}」相关任务，"
        f"输出 __ 份可展示成果，并在简历中显式写出上述关键词"
    )
    return {
        "section": _SECTION_LABELS.get(section_key, "经历"),
        "original": original,
        "suggested": suggested,
        "focus": "把 JD 缺失关键词写入经历句，而非只堆技能栏",
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
        if len(line) < 6:
            continue
        items.append(
            {
                "section": _SECTION_LABELS.get(key, "经历"),
                "original": line[:120],
                "suggested": _rewrite_weak_experience(line, target, missing, tools),
                "focus": "STAR 结构：背景 → 行动 → 量化结果",
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
    originals = [item.get("original", "") for item in base_items if item.get("original")]
    if not originals:
        originals = [
            line.strip()
            for values in sections.values()
            if isinstance(values, list)
            for line in values[:2]
            if str(line).strip()
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
        "1. 每条采用 STAR 或「结果前置 + 行动 + 方法」结构；\n"
        "2. 必须给出完整改写句，不要只写建议或点评；\n"
        "3. 尽量融入目标岗位与缺失关键词；\n"
        "4. 无真实数据处用 __ 占位，不要编造具体数字；\n"
        "5. 只返回 JSON，不要 Markdown。\n"
        '格式：{"summary":"一句话总结","items":[{"section":"板块","original":"原文","suggested":"改写","focus":"优化点"}]}\n'
        f"目标岗位：{target_label}\n"
        f"缺失关键词：{match_result.get('missing_keywords', [])}\n"
        f"已匹配关键词：{match_result.get('matched_keywords', [])}\n"
        f"待优化原文：{originals}\n"
    )
    if offline_samples:
        prompt += f"离线改写参考（请在此基础上润色，不要简单复述诊断）：\n" + "\n".join(offline_samples) + "\n"
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
        return {
            "summary": data.get("summary") or f"AI 围绕「{target_label}」生成 {len(normalized)} 条深度改写参考。",
            "items": normalized,
            "target_position": target_label,
            "mode": "deepseek",
        }
    except Exception as exc:
        if raise_on_failure:
            raise RuntimeError(f"AI 深度改写失败：{exc}") from exc
        return None
