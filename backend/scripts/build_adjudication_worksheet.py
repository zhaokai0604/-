"""Build an empty adjudication worksheet from A/B disagreement JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "docs" / "testing" / "annotation_disagreements_A_B_common15.json"
DEFAULT_OUTPUT = ROOT / "docs" / "testing" / "A池裁决工作表.json"

PRIORITY = {
    "resume-009": "P0",
    "resume-005": "P0",
    "resume-013": "P0",
    "resume-015": "P0",
    "resume-002": "P1",
    "resume-003": "P1",
    "resume-004": "P1",
    "resume-006": "P1",
    "resume-012": "P1",
    "resume-014": "P1",
    "resume-007": "P2",
    "resume-008": "P2",
    "resume-010": "P2",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="从分歧报告生成裁决工作表")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    rows = []
    for item in payload.get("disagreements") or []:
        case_id = str(item.get("id") or "")
        fields = item.get("fields") or {}
        rows.append(
            {
                "id": case_id,
                "priority": PRIORITY.get(case_id, "P1"),
                "status": "pending",
                "disputed_fields": sorted(fields.keys()),
                "annotator_a": {k: v.get("annotator_a") for k, v in fields.items()},
                "annotator_b": {k: v.get("annotator_b") for k, v in fields.items()},
                "adjudicated_gold_sections": None,
                "adjudicated_parse_quality": None,
                "adjudicated_resume_quality": None,
                "adjudicated_issue_types": None,
                "adjudicator": "",
                "adjudicated_at": "",
                "rationale": "",
            }
        )

    rows.sort(key=lambda row: (row["priority"], row["id"]))
    result = {
        "version": 1,
        "policy": "third_party_adjudication_does_not_overwrite_raw",
        "source": str(args.input.relative_to(ROOT)).replace("\\", "/"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pending": len(rows),
        "done": 0,
        "cases": rows,
        "instructions": (
            "填写 adjudicated_* 字段后将 status 改为 done；"
            "保留 annotator_a/b；完成后才可导出黄金标签。"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "pending": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
