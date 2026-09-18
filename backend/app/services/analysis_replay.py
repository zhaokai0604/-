"""基于已落库分析结果重放「实时解析流」事件（演示友好、无需重复 OCR）。"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from app.services.score_engine import SECTION_LABELS, label_for_score


def _event(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps({"event": event, **data}, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def iter_replay_events(
    record_payload: dict[str, Any],
    *,
    pace_seconds: float = 0.08,
) -> Iterator[str]:
    sections = record_payload.get("sections") if isinstance(record_payload.get("sections"), dict) else {}
    match = record_payload.get("match_result") if isinstance(record_payload.get("match_result"), dict) else {}
    scores = record_payload.get("scores") if isinstance(record_payload.get("scores"), dict) else {}
    low_snr = record_payload.get("low_snr_zones") if isinstance(record_payload.get("low_snr_zones"), list) else []
    skill_graph = record_payload.get("skill_graph") if isinstance(record_payload.get("skill_graph"), dict) else {}
    rewrite = record_payload.get("rewrite_preview") if isinstance(record_payload.get("rewrite_preview"), dict) else {}
    optimized = rewrite.get("optimized_resume") if isinstance(rewrite.get("optimized_resume"), dict) else {}

    yield _event("step", {"step": "extract", "message": "正在提取正文与结构…"})
    line_index = 0
    for key, values in sections.items():
        if not isinstance(values, list):
            continue
        label = SECTION_LABELS.get(key, key)
        for line in values[:6]:
            text = str(line).strip()
            if not text:
                continue
            yield _event(
                "parse_line",
                {
                    "index": line_index,
                    "section": key,
                    "text": text[:180],
                    "message": f"正在阅读「{label}」… {text[:40]}",
                },
            )
            line_index += 1
            if pace_seconds > 0:
                time.sleep(pace_seconds)
        if values:
            yield _event(
                "section_found",
                {
                    "section": key,
                    "sample": str(values[0])[:80],
                    "message": f"🟢 已提取{label}… 发现「{str(values[0])[:40]}」",
                },
            )

    yield _event("step", {"step": "match", "message": "🟡 正在匹配岗位关键词…"})
    for word in (match.get("matched_keywords") or record_payload.get("matched_keywords") or [])[:8]:
        yield _event("keyword_hit", {"keyword": word, "message": f"命中「{word}」"})
        if pace_seconds > 0:
            time.sleep(pace_seconds * 0.7)
    for word in (match.get("missing_keywords") or record_payload.get("missing_keywords") or [])[:8]:
        yield _event("keyword_miss", {"keyword": word, "message": f"缺失「{word}」"})
        if pace_seconds > 0:
            time.sleep(pace_seconds * 0.7)

    for zone in low_snr[:5]:
        if not isinstance(zone, dict):
            continue
        yield _event(
            "low_snr",
            {
                "text": str(zone.get("text") or "")[:120],
                "reason": zone.get("reason") or "",
                "message": f"🔵 标记低信噪比区：{str(zone.get('text') or '')[:36]}",
            },
        )

    for hint in skill_graph.get("hints") or []:
        yield _event("skill_hint", {"message": hint.get("message"), "hint": hint})

    yield _event("step", {"step": "score", "message": "正在计算六维评分…"})
    for key, value in scores.items():
        yield _event(
            "score_dim",
            {
                "dimension": key,
                "value": value,
                "message": f"{label_for_score(key)} → {value}",
            },
        )
        if pace_seconds > 0:
            time.sleep(pace_seconds * 0.5)

    yield _event(
        "done",
        {
            "message": "🟢 分析完成，已生成基于初稿的优化稿",
            "total_score": record_payload.get("total_score"),
            "change_count": optimized.get("change_count", 0),
            "record_id": record_payload.get("record_id"),
        },
    )
