"""Evaluate team-labeled redacted resume section annotations.

Input JSON contains only redacted text and labels. It never creates labels and
never calls an external model, so it can be used as a reproducible gate before
any parser rule or matching-model update.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.parser import detect_sections  # noqa: E402
from app.services.pipeline_utils import normalize_sections  # noqa: E402

SENSITIVE_PATTERNS = (
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"[1-9]\d{5}(?:19|20)\d{9}[\dXx]"),
)


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="评估脱敏真实简历板块标注")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    if not cases:
        raise SystemExit("标注集为空：请先完成 A 池人工标注。")

    tp = fp = fn = 0
    stats: dict[str, dict[str, int]] = {}
    errors: list[dict[str, object]] = []
    for case in cases:
        text = str(case.get("text") or "")
        if any(pattern.search(text) for pattern in SENSITIVE_PATTERNS):
            raise SystemExit(f"检测到可能的敏感信息，请先脱敏: {case.get('id')}")
        gold = set(case.get("gold_sections") or [])
        pred = {key for key, lines in normalize_sections(detect_sections(text)).items() if lines}
        hit, miss, extra = gold & pred, gold - pred, pred - gold
        tp += len(hit)
        fn += len(miss)
        fp += len(extra)
        for key in gold | pred:
            item = stats.setdefault(key, {"tp": 0, "fp": 0, "fn": 0})
            item["tp"] += int(key in hit)
            item["fp"] += int(key in extra)
            item["fn"] += int(key in miss)
        if miss or extra:
            errors.append({"id": case.get("id"), "miss": sorted(miss), "extra": sorted(extra)})

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    result = {
        "cases": len(cases),
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(_f1(precision, recall), 4),
        "per_section": {},
        "errors": errors,
        "label_policy": payload.get("label_policy", "team_double_annotation"),
    }
    for key, item in sorted(stats.items()):
        p = item["tp"] / (item["tp"] + item["fp"]) if item["tp"] + item["fp"] else 0.0
        r = item["tp"] / (item["tp"] + item["fn"]) if item["tp"] + item["fn"] else 0.0
        result["per_section"][key] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(_f1(p, r), 4),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
