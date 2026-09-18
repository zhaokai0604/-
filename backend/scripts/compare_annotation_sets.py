"""Compare two independent redacted resume annotation exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FIELDS = ("gold_sections", "parse_quality", "resume_quality", "issue_types")


def load(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    return {str(case.get("id")): case for case in cases if case.get("id")}


def main() -> int:
    parser = argparse.ArgumentParser(description="比较两名标注员的独立标注结果")
    parser.add_argument("--a", type=Path, required=True, help="标注员 A 的 JSON")
    parser.add_argument("--b", type=Path, required=True, help="标注员 B 的 JSON")
    parser.add_argument("--output", type=Path, required=True, help="UTF-8 分歧报告")
    parser.add_argument("--common-only", action="store_true", help="只比较两份文件共同拥有的样本 ID")
    args = parser.parse_args()

    left, right = load(args.a), load(args.b)
    if args.common_only:
        common = set(left) & set(right)
        left = {key: left[key] for key in common}
        right = {key: right[key] for key in common}
    ids = sorted(set(left) | set(right))
    disagreements: list[dict[str, object]] = []
    field_counts = {field: 0 for field in FIELDS}
    missing_a, missing_b = sorted(set(right) - set(left)), sorted(set(left) - set(right))
    for case_id in ids:
        a, b = left.get(case_id), right.get(case_id)
        if not a or not b:
            continue
        diff = {}
        for field in FIELDS:
            av = sorted(a.get(field) or []) if field in ("gold_sections", "issue_types") else a.get(field)
            bv = sorted(b.get(field) or []) if field in ("gold_sections", "issue_types") else b.get(field)
            if av != bv:
                field_counts[field] += 1
                diff[field] = {"annotator_a": av, "annotator_b": bv}
        if diff:
            disagreements.append({"id": case_id, "fields": diff})

    result = {
        "version": 1,
        "policy": "independent_two_annotator_annotation",
        "cases_a": len(left),
        "cases_b": len(right),
        "common_cases": len(set(left) & set(right)),
        "missing_in_a": missing_a,
        "missing_in_b": missing_b,
        "disagreement_counts": field_counts,
        "disagreements": disagreements,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("cases_a", "cases_b", "common_cases", "disagreement_counts")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
