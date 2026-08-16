"""Create group-disjoint train/validation/test splits for match evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="按岗位组切分岗位匹配评测集")
    parser.add_argument("--input", type=Path, default=Path("../data/eval/match_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("../data/eval/match_splits"))
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    groups: dict[str, list[dict]] = {}
    for case in cases:
        group = str(case.get("id") or "unknown").split("-", 1)[0]
        groups.setdefault(group, []).append(case)
    ordered = sorted(groups)
    test_count = max(1, round(len(ordered) * 0.2))
    validation_count = max(1, round(len(ordered) * 0.15))
    test_groups = set(ordered[-test_count:])
    validation_groups = set(ordered[-test_count - validation_count : -test_count])
    train_groups = set(ordered) - test_groups - validation_groups

    def collect(selected: set[str]) -> list[dict]:
        return [case for group in ordered if group in selected for case in groups[group]]

    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": 1,
        "policy": "group_disjoint_by_case_id_prefix",
        "source_cases": len(cases),
        "groups": {"train": sorted(train_groups), "validation": sorted(validation_groups), "test": sorted(test_groups)},
        "warning": "仅切分数据；正式测试前必须用 train split 重新训练/拟合，测试集只使用一次。",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, selected in (("train", train_groups), ("validation", validation_groups), ("test", test_groups)):
        (output / f"{name}.json").write_text(
            json.dumps({"version": 1, "cases": collect(selected)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"train": len(collect(train_groups)), "validation": len(collect(validation_groups)), "test": len(collect(test_groups)), "groups": manifest["groups"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
