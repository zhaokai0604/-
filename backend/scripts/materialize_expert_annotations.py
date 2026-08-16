"""Create the first-pass expert annotation set from the local A pool.

The source files are already in a temporary local directory. This helper applies
one more explicit redaction pass before writing the UTF-8 evaluation JSON.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


GOLD = {
    "A-01": (["basic_info", "education", "campus", "skills", "summary"], "high", 4, ["layout_fragmentation"]),
    "A-02": (["basic_info", "education", "internship", "projects", "campus", "skills", "awards", "summary"], "medium", 4, ["layout_fragmentation"]),
    "A-03": (["basic_info", "education", "internship", "campus", "skills", "summary"], "high", 5, ["ocr_noise"]),
    "A-04": (["basic_info", "education", "internship", "campus", "skills", "summary"], "medium", 3, ["layout_fragmentation", "weak_structure"]),
    "A-05": (["basic_info", "education", "internship", "campus", "skills", "awards", "summary"], "high", 3, ["missing_metrics"]),
    "A-06": (["basic_info", "education", "internship", "campus", "skills", "awards", "summary"], "high", 4, ["missing_metrics"]),
    "A-07": (["basic_info", "education", "internship", "campus", "skills", "summary"], "medium", 3, ["layout_fragmentation", "weak_structure"]),
    "A-08": (["basic_info", "education", "projects", "skills", "summary"], "high", 5, ["missing_internship"]),
    "A-09": (["basic_info", "education", "internship", "skills", "summary"], "medium", 4, ["ocr_noise", "missing_metrics"]),
    "A-10": (["basic_info", "education", "internship", "skills", "summary"], "medium", 3, ["layout_fragmentation", "weak_structure"]),
    "A-11": (["basic_info", "education", "internship", "campus", "skills", "summary"], "medium", 5, ["layout_fragmentation"]),
    "A-12": (["basic_info", "education", "internship", "campus", "skills", "summary"], "high", 5, []),
    "A-13": (["basic_info", "education", "internship", "campus", "skills", "awards", "summary"], "medium", 4, ["layout_fragmentation"]),
    "A-14": (["basic_info", "education", "internship", "campus", "skills", "awards", "summary"], "high", 4, ["missing_projects"]),
    "A-15": (["basic_info", "education", "internship", "projects", "skills", "summary"], "high", 5, ["missing_campus", "over_scored_risk"]),
}

PERSON_NAMES = (
    "刘诗诗", "吕盼龙", "吴予桐", "吴晨曦", "张思涵", "张梓萌", "朱雪龑",
    "李伟东", "李相夷", "李雨欣", "林溪", "橙子爱吃糖", "王舒涵", "许怀瑾", "陈无敌",
)

SENSITIVE_PHRASES = (
    "杭州市萧山卫生中等专业学校", "杭州市第三人民医院", "和平西路小学", "渝中区人和街小学",
    "陕西省电子工业学校", "国家能源集团陕西神延煤炭有限责任公司", "榆林市高新区白氏兄弟烧烤兴达路店",
    "上海**科技公司", "陕西省西安",
)


def redact(text: str) -> str:
    for value in PERSON_NAMES:
        text = text.replace(value, "[姓名]")
    for value in SENSITIVE_PHRASES:
        text = text.replace(value, "[机构]")
    text = re.sub(r"(?<!\d)1[3-9]\d[\s-]?\d{4}[\s-]?\d{4}(?!\d)", "[手机号]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[邮箱]", text)
    text = re.sub(r"(?i)(电话|手机号码?|联系电话|微信号)\s*[:：]?\s*[^\n]{0,30}", r"\1：[联系方式]", text)
    return text


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: materialize_expert_annotations.py POOL_DIR OUTPUT_JSON")
    pool_dir = Path(sys.argv[1])
    output = Path(sys.argv[2])
    report = json.loads((pool_dir / "classify_report.json").read_text(encoding="utf-8"))
    rows = [row for row in report["rows"] if row.get("pool") == "A"]
    rows.sort(key=lambda row: row["file"])
    cases = []
    for index, row in enumerate(rows, 1):
        case_id = f"A-{index:02d}"
        gold_sections, parse_quality, resume_quality, issues = GOLD[case_id]
        text = redact((pool_dir / "pool_A" / row["file"]).read_text(encoding="utf-8"))
        cases.append(
            {
                "id": case_id,
                "source_type": row.get("source_type"),
                "text": text,
                "gold_sections": gold_sections,
                "annotator_a": "codex_expert_initial",
                "annotator_b": "",
                "adjudicated_by": "",
                "parse_quality": parse_quality,
                "resume_quality": resume_quality,
                "match_quality": None,
                "issue_types": issues,
                "over_scored": "over_scored_risk" in issues,
                "missed_sections": [],
                "notes": "首轮专家初标；需本人复核后作为正式评测集。",
            }
        )
    payload = {
        "version": 1,
        "label_policy": "single_expert_initial_annotation_pending_user_review",
        "annotation_source": "codex_expert_initial",
        "cases": cases,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output} cases={len(cases)} encoding=utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
