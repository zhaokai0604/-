"""基于初稿生成完整优化稿（非整句建议列表）。"""

from __future__ import annotations

import re
from typing import Any

_SECTION_LABELS = {
    "basic_info": "基本信息",
    "education": "教育经历",
    "internship": "实习经历",
    "projects": "项目经历",
    "campus": "校园实践",
    "skills": "技能特长",
    "awards": "荣誉奖项",
    "summary": "自我评价/求职意向",
    "others": "其他",
}

_PLACEHOLDER_HINT = "【待补充：职责细节或真实产出，勿编造】"


def build_optimized_resume(
    sections: dict[str, list[str]],
    rewrite_items: list[dict[str, Any]],
    *,
    target_position: str = "",
    skill_hints: list[dict[str, Any]] | None = None,
    summary: str = "",
    mode: str = "offline_star",
) -> dict[str, Any]:
    optimized = {
        key: [str(line) for line in (value or []) if str(line).strip()]
        for key, value in sections.items()
        if isinstance(value, list) and not str(key).startswith("_")
    }
    replacements: dict[str, str] = {}
    for item in rewrite_items or []:
        if not isinstance(item, dict):
            continue
        original = re.sub(r"\s+", " ", str(item.get("original") or "").strip())
        suggested = str(item.get("suggested") or "").strip()
        if not original or not suggested:
            continue
        # 禁止用编造职责覆盖链接/联系方式行
        if re.search(r"https?://|www\.|shoturl\.|个人作品|现居|身高|邮箱|手机|电话", original, re.I):
            continue
        if original.startswith("（待补充"):
            # 附加提示，不当替换键
            continue
        replacements[original] = suggested

    diffs: list[dict[str, str]] = []
    for key, lines in list(optimized.items()):
        new_lines: list[str] = []
        for line in lines:
            normalized = re.sub(r"\s+", " ", line.strip())
            suggested = replacements.get(normalized)
            if suggested:
                new_lines.append(suggested)
                diffs.append(
                    {
                        "section": _SECTION_LABELS.get(key, key),
                        "section_key": key,
                        "original": normalized,
                        "optimized": suggested,
                        "change_type": "rewrite",
                    }
                )
            else:
                new_lines.append(line)
        optimized[key] = new_lines

    for original, suggested in replacements.items():
        if any(d["original"] == original for d in diffs):
            continue
        # 原文未精确落在分节中时，附加到 projects/others
        bucket = "projects" if optimized.get("projects") is not None else "others"
        optimized.setdefault(bucket, [])
        optimized[bucket].append(suggested)
        diffs.append(
            {
                "section": _SECTION_LABELS.get(bucket, bucket),
                "section_key": bucket,
                "original": original,
                "optimized": suggested,
                "change_type": "append_rewrite",
            }
        )

    for hint in skill_hints or []:
        if not isinstance(hint, dict):
            continue
        if hint.get("type") != "parent_skill":
            continue
        suggest_skill = str(hint.get("suggest_skill") or "").strip()
        hit_skill = str(hint.get("hit_skill") or "").strip()
        if not suggest_skill:
            continue
        line = (
            f"{suggest_skill}：已具备{hit_skill or '相关'}基础，"
            f"可补充问题定义→分析方法→业务结论的整体描述{_PLACEHOLDER_HINT}"
        )
        optimized.setdefault("skills", [])
        if not any(suggest_skill in existing for existing in optimized["skills"]):
            optimized["skills"].append(line)
            diffs.append(
                {
                    "section": _SECTION_LABELS.get("skills", "技能特长"),
                    "section_key": "skills",
                    "original": "",
                    "optimized": line,
                    "change_type": "skill_graph",
                }
            )

    ordered_keys = [
        "basic_info",
        "education",
        "internship",
        "projects",
        "campus",
        "skills",
        "awards",
        "summary",
        "others",
    ]
    document_lines: list[str] = []
    if target_position:
        document_lines.append(f"目标岗位：{target_position}")
        document_lines.append("")
    for key in ordered_keys:
        lines = optimized.get(key) or []
        if not lines:
            continue
        document_lines.append(_SECTION_LABELS.get(key, key))
        document_lines.extend(lines)
        document_lines.append("")

    for key, lines in optimized.items():
        if key in ordered_keys or not lines:
            continue
        document_lines.append(_SECTION_LABELS.get(key, key))
        document_lines.extend(lines)
        document_lines.append("")

    return {
        "title": f"{target_position or '简历'}优化稿" if target_position else "简历优化稿",
        "target_position": target_position,
        "summary": summary
        or f"已在初稿基础上生成优化稿，共 {len(diffs)} 处改动；不足处保留待补充标记，未编造经历。",
        "mode": mode,
        "sections": optimized,
        "document_text": "\n".join(document_lines).strip(),
        "diffs": diffs,
        "change_count": len(diffs),
    }


def attach_optimized_resume(
    rewrite_preview: dict[str, Any],
    sections: dict[str, list[str]],
    *,
    skill_hints: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    preview = dict(rewrite_preview or {})
    optimized = build_optimized_resume(
        sections,
        preview.get("items") or [],
        target_position=str(preview.get("target_position") or ""),
        skill_hints=skill_hints,
        summary=str(preview.get("summary") or ""),
        mode=str(preview.get("mode") or "offline_star"),
    )
    preview["optimized_resume"] = optimized
    return preview
