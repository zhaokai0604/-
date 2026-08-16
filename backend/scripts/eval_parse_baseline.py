"""解析模块评测：对 gold_sections 计算 Precision / Recall / F1。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "parse-eval-secret")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings

get_settings.cache_clear()

from app.services.parser import detect_sections
from app.services.pipeline_utils import normalize_sections


def _predicted_sections(text: str) -> set[str]:
    sections = normalize_sections(detect_sections(text))
    return {key for key, lines in sections.items() if lines}


def _f1(precision: float, recall: float) -> float:
    if precision + recall <= 1e-12:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def main() -> int:
    settings = get_settings()
    path = settings.data_dir / "eval" / "parse_cases.json"
    if not path.exists():
        print("missing parse_cases.json, run build_parse_eval_set.py first")
        return 1
    cases = json.loads(path.read_text(encoding="utf-8")).get("cases") or []
    if not cases:
        print("empty parse eval set")
        return 1

    section_keys = sorted({key for case in cases for key in (case.get("gold_sections") or [])})
    # micro
    tp = fp = fn = 0
    # per-section
    stats = {key: {"tp": 0, "fp": 0, "fn": 0} for key in section_keys}
    rows = []

    for case in cases:
        gold = set(case.get("gold_sections") or [])
        pred = _predicted_sections(str(case.get("text") or ""))
        hit = gold & pred
        miss = gold - pred
        extra = pred - gold
        tp += len(hit)
        fn += len(miss)
        fp += len(extra)
        for key in hit:
            if key in stats:
                stats[key]["tp"] += 1
        for key in miss:
            if key in stats:
                stats[key]["fn"] += 1
        for key in extra:
            stats.setdefault(key, {"tp": 0, "fp": 0, "fn": 0})
            stats[key]["fp"] += 1
        rows.append(
            {
                "id": case.get("id"),
                "gold": sorted(gold),
                "pred": sorted(pred),
                "hit": sorted(hit),
                "miss": sorted(miss),
                "extra": sorted(extra),
            }
        )

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = _f1(precision, recall)

    print("=== 解析模块评测 ===")
    for row in rows:
        print(
            f"{row['id']}: hit={row['hit']} miss={row['miss']} extra={row['extra']}"
        )
    print("---")
    print(f"cases      = {len(cases)}")
    print(f"micro P    = {precision:.4f}")
    print(f"micro R    = {recall:.4f}")
    print(f"micro F1   = {f1:.4f}")
    print("per-section F1:")
    for key in sorted(stats):
        s = stats[key]
        p = s["tp"] / (s["tp"] + s["fp"]) if (s["tp"] + s["fp"]) else 0.0
        r = s["tp"] / (s["tp"] + s["fn"]) if (s["tp"] + s["fn"]) else 0.0
        print(f"  {key:12s} P={p:.3f} R={r:.3f} F1={_f1(p, r):.3f}")

    out = settings.data_dir / "eval" / "parse_baseline_last.json"
    out.write_text(
        json.dumps(
            {
                "cases": len(cases),
                "micro_precision": round(precision, 4),
                "micro_recall": round(recall, 4),
                "micro_f1": round(f1, 4),
                "per_section": {
                    key: {
                        "precision": round(
                            stats[key]["tp"] / (stats[key]["tp"] + stats[key]["fp"])
                            if (stats[key]["tp"] + stats[key]["fp"])
                            else 0.0,
                            4,
                        ),
                        "recall": round(
                            stats[key]["tp"] / (stats[key]["tp"] + stats[key]["fn"])
                            if (stats[key]["tp"] + stats[key]["fn"])
                            else 0.0,
                            4,
                        ),
                        "f1": round(
                            _f1(
                                stats[key]["tp"] / (stats[key]["tp"] + stats[key]["fp"])
                                if (stats[key]["tp"] + stats[key]["fp"])
                                else 0.0,
                                stats[key]["tp"] / (stats[key]["tp"] + stats[key]["fn"])
                                if (stats[key]["tp"] + stats[key]["fn"])
                                else 0.0,
                            ),
                            4,
                        ),
                    }
                    for key in sorted(stats)
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
