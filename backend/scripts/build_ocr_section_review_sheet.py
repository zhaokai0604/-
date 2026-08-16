"""Create an empty OCR section-level sampling review worksheet."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs" / "testing" / "PDF_OCR板块抽样工作表.json"

LAYOUT_CYCLE = (
    "single",
    "single",
    "dual",
    "dual",
    "table",
    "table",
    "scan_noise",
    "scan_noise",
    "dual",
    "scan_noise",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 PDF OCR 板块抽样空表")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    count = max(8, min(10, int(args.count)))
    cases = []
    for idx in range(1, count + 1):
        cases.append(
            {
                "sample_id": f"OCR-{idx:02d}",
                "layout_type": LAYOUT_CYCLE[(idx - 1) % len(LAYOUT_CYCLE)],
                "source_ref": "",
                "ocr_readable": True,
                "human_sections": [],
                "system_sections": [],
                "section_hit": [],
                "section_false": [],
                "section_miss": [],
                "alert_reasonable": "",
                "status": "pending",
                "note": "",
            }
        )

    result = {
        "version": 1,
        "experiment": "pdf_ocr_section_sample_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_count": count,
        "policy": (
            "OCR 可读率与板块识别分列；本表只做人工抽样，"
            "不写入平台业务库，不用于微调。"
        ),
        "metrics_layers": {
            "L1": "分析成功率（链路）",
            "L2": "文本可读率（含 OCR）",
            "L3": "板块抽检命中 / 告警合理性（本表）",
        },
        "cases": cases,
        "summary": {
            "done": 0,
            "section_exact_match_rate": None,
            "alert_reasonable_rate": None,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "count": count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
