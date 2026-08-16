"""轻量岗位技能图谱：父子层级 + 同义词命中提示。"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.core.config import settings


@lru_cache(maxsize=1)
def load_skill_graph() -> dict[str, Any]:
    graph_path = settings.data_dir / "skill_graph.json"
    if not graph_path.exists():
        return {"nodes": [], "by_id": {}, "parent_of": {}}
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = payload.get("nodes") if isinstance(payload, dict) else []
    by_id = {str(node["id"]): node for node in nodes if isinstance(node, dict) and node.get("id")}
    parent_of: dict[str, str] = {}
    for node_id, node in by_id.items():
        for child_id in node.get("children") or []:
            parent_of[str(child_id)] = node_id
    return {"nodes": list(by_id.values()), "by_id": by_id, "parent_of": parent_of}


def build_skill_graph_hints(
    resume_text: str,
    matched_keywords: list[str] | None = None,
    missing_keywords: list[str] | None = None,
    target_position: str = "",
    limit: int = 5,
) -> dict[str, Any]:
    graph = load_skill_graph()
    by_id: dict[str, dict[str, Any]] = graph.get("by_id") or {}
    parent_of: dict[str, str] = graph.get("parent_of") or {}
    haystack = " ".join(
        [
            resume_text or "",
            " ".join(matched_keywords or []),
            target_position or "",
        ]
    ).lower()

    hit_ids: list[str] = []
    for node_id, node in by_id.items():
        aliases = [str(node.get("name") or "")] + [str(a) for a in (node.get("aliases") or [])]
        if any(alias and alias.lower() in haystack for alias in aliases):
            hit_ids.append(node_id)

    hints: list[dict[str, str]] = []
    seen: set[str] = set()
    for child_id in hit_ids:
        parent_id = parent_of.get(child_id)
        if not parent_id or parent_id in hit_ids:
            continue
        parent = by_id.get(parent_id) or {}
        child = by_id.get(child_id) or {}
        key = f"{child_id}->{parent_id}"
        if key in seen:
            continue
        seen.add(key)
        child_name = str(child.get("name") or child_id)
        parent_name = str(parent.get("name") or parent_id)
        hints.append(
            {
                "type": "parent_skill",
                "hit_skill": child_name,
                "suggest_skill": parent_name,
                "message": (
                    f"您已掌握子技能「{child_name}」，建议补充父级能力「{parent_name}」"
                    f"的整体视角描述（问题定义 → 方法 → 结果）。"
                ),
            }
        )
        if len(hints) >= limit:
            break

    missing = [str(k).strip() for k in (missing_keywords or []) if str(k).strip()]
    for word in missing[: max(0, limit - len(hints))]:
        hints.append(
            {
                "type": "missing_keyword",
                "hit_skill": "",
                "suggest_skill": word,
                "message": f"岗位要求中的「{word}」尚未在简历中体现，可在技能或项目中补充真实经历。",
            }
        )

    return {
        "hit_skills": [str((by_id.get(i) or {}).get("name") or i) for i in hit_ids[:12]],
        "hints": hints[:limit],
    }
