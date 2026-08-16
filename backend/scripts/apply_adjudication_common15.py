"""Apply third-party adjudication for A-pool common-15 disagreements."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "标注协作包_脱敏" / "数据集"
ANNOT_A = ROOT / "标注协作包_脱敏" / "标注结果" / "real_parse_annotations A组_前15条.json"
DISAGREEMENTS = ROOT / "docs" / "testing" / "annotation_disagreements_A_B_common15.json"
WORKSHEET = ROOT / "docs" / "testing" / "A池裁决工作表.json"
GOLD_OUT = ROOT / "data" / "eval" / "real_parse_annotations_adjudicated_common15.json"

ADJUDICATOR = "third_party_rules_v1"
CASE_IDS = [f"resume-{i:03d}" for i in range(1, 16)]

FIELDS = ("gold_sections", "parse_quality", "resume_quality", "issue_types")

# Third-party rulings keyed by case id (sorted section lists).
ADJUDICATIONS: dict[str, dict] = {
    "resume-001": {
        "gold_sections": ["basic_info", "education", "internship", "skills", "summary"],
        "parse_quality": "medium",
        "resume_quality": 2,
        "issue_types": ["layout_fragmentation", "missing_projects"],
        "rationale": "A/B一致：有教育、销售经历与技能，版式双栏重复，无独立项目块。",
    },
    "resume-002": {
        "gold_sections": [
            "basic_info",
            "education",
            "internship",
            "projects",
            "skills",
            "summary",
        ],
        "parse_quality": "high",
        "resume_quality": 5,
        "issue_types": [],
        "rationale": "无校园/荣誉独立块；奖学金嵌入教育段；综合素质段作summary；正文模块边界清晰。",
    },
    "resume-003": {
        "gold_sections": [
            "awards",
            "basic_info",
            "campus",
            "education",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 2,
        "issue_types": [
            "layout_fragmentation",
            "ocr_noise",
            "missing_internship",
            "missing_projects",
        ],
        "rationale": "正文有教育背景与奖学金；无公司实习/项目；双栏碎片与竖排噪声明显。",
    },
    "resume-004": {
        "gold_sections": [
            "awards",
            "basic_info",
            "education",
            "internship",
            "projects",
            "skills",
            "summary",
        ],
        "parse_quality": "high",
        "resume_quality": 5,
        "issue_types": [],
        "rationale": "无校园经历独立块；项目实践与实习段落完整可读，结构清楚。",
    },
    "resume-005": {
        "gold_sections": [
            "awards",
            "basic_info",
            "campus",
            "education",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 2,
        "issue_types": [
            "layout_fragmentation",
            "ocr_noise",
            "weak_structure",
            "missing_internship",
            "missing_projects",
        ],
        "rationale": "有教育、荣誉、辅导员校园职责与自我评价；无正式公司实习/项目；OCR致字段碎裂。",
    },
    "resume-006": {
        "gold_sections": [
            "basic_info",
            "education",
            "internship",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 4,
        "issue_types": ["layout_fragmentation", "missing_projects"],
        "rationale": "实习/工作经历量化充分；奖学金一句在教育段不单独标awards；无项目段。",
    },
    "resume-007": {
        "gold_sections": [
            "basic_info",
            "campus",
            "education",
            "internship",
            "projects",
            "skills",
            "summary",
        ],
        "parse_quality": "high",
        "resume_quality": 4,
        "issue_types": [],
        "rationale": "板块沿用A/B一致标注；多科室实习与校园活动完整，版式可读性高，内容质量取4。",
    },
    "resume-008": {
        "gold_sections": [
            "awards",
            "basic_info",
            "campus",
            "education",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 3,
        "issue_types": [
            "layout_fragmentation",
            "ocr_noise",
            "missing_internship",
            "missing_projects",
        ],
        "rationale": "板块可识别但基本信息/email碎裂；无实习与项目；校园与奖项列表可读。",
    },
    "resume-009": {
        "gold_sections": [
            "awards",
            "basic_info",
            "campus",
            "education",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 3,
        "issue_types": [
            "layout_fragmentation",
            "ocr_noise",
            "weak_structure",
            "missing_internship",
            "missing_projects",
        ],
        "rationale": "A空标错误；乱序但可辨基本/教育/校园/荣誉/技能/评价；无实习项目。",
    },
    "resume-010": {
        "gold_sections": [
            "awards",
            "basic_info",
            "campus",
            "education",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 3,
        "issue_types": ["layout_fragmentation", "missing_projects"],
        "rationale": "荣誉与校园活动丰富；有短期工作经验故不勾missing_internship；无项目段。",
    },
    "resume-011": {
        "gold_sections": [
            "awards",
            "basic_info",
            "campus",
            "education",
            "internship",
            "projects",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 5,
        "issue_types": ["layout_fragmentation"],
        "rationale": "A/B一致：八板块齐全；末尾双栏重复致layout_fragmentation。",
    },
    "resume-012": {
        "gold_sections": [
            "basic_info",
            "campus",
            "education",
            "projects",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 2,
        "issue_types": ["layout_fragmentation", "missing_internship"],
        "rationale": "课程项目与专业技能段均存在；无实习；末尾重复片段致版式碎片。",
    },
    "resume-013": {
        "gold_sections": [
            "awards",
            "basic_info",
            "campus",
            "education",
            "projects",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 3,
        "issue_types": [
            "layout_fragmentation",
            "weak_structure",
            "missing_internship",
        ],
        "rationale": "乱序但可辨教育/个人账号项目/校新媒体/奖项；无公司实习；结构弱。",
    },
    "resume-014": {
        "gold_sections": [
            "awards",
            "basic_info",
            "campus",
            "education",
            "skills",
            "summary",
        ],
        "parse_quality": "medium",
        "resume_quality": 3,
        "issue_types": [
            "layout_fragmentation",
            "missing_internship",
            "missing_metrics",
            "missing_projects",
        ],
        "rationale": "教育背景与在校学生会块明确；无实习/项目；经历量化不足。",
    },
    "resume-015": {
        "gold_sections": [
            "basic_info",
            "education",
            "internship",
            "skills",
            "summary",
        ],
        "parse_quality": "high",
        "resume_quality": 5,
        "issue_types": ["missing_projects"],
        "rationale": "工作经历作internship；证书在技能段不单独标awards；无校园/项目；结构清晰。",
    },
}


def _sort_sections(items: list[str] | None) -> list[str]:
    order = [
        "basic_info",
        "education",
        "internship",
        "projects",
        "campus",
        "skills",
        "awards",
        "summary",
    ]
    present = set(items or [])
    return [s for s in order if s in present]


def _sort_issues(items: list[str] | None) -> list[str]:
    order = [
        "layout_fragmentation",
        "ocr_noise",
        "weak_structure",
        "missing_internship",
        "missing_projects",
        "missing_metrics",
        "over_scored_risk",
    ]
    present = set(items or [])
    return [s for s in order if s in present]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_annotator_b(
    case_id: str,
    annot_a: dict,
    disagreements: dict[str, dict],
) -> dict[str, object]:
    """Reconstruct annotator B labels from disagreement report + A for agreed fields."""
    fields = disagreements.get(case_id, {})
    out: dict[str, object] = {}
    for field in FIELDS:
        if field in fields:
            out[field] = fields[field]["annotator_b"]
        else:
            out[field] = annot_a.get(field)
    if field := "gold_sections":
        if isinstance(out.get(field), list):
            out[field] = _sort_sections(out[field])
    if field := "issue_types":
        if isinstance(out.get(field), list):
            out[field] = _sort_issues(out[field])
    return out


def main() -> int:
    annot_a_payload = load_json(ANNOT_A)
    annot_a_map = {
        c["id"]: c
        for c in annot_a_payload["cases"]
        if c.get("id") in CASE_IDS
    }

    disagree_payload = load_json(DISAGREEMENTS)
    disagree_map = {d["id"]: d["fields"] for d in disagree_payload.get("disagreements", [])}

    worksheet = load_json(WORKSHEET)
    adjudicated_at = datetime.now(timezone.utc).isoformat()

    worksheet_cases_by_id = {c["id"]: c for c in worksheet["cases"]}
    for case_id in CASE_IDS:
        adj = ADJUDICATIONS[case_id]
        row = worksheet_cases_by_id.get(case_id)
        if row is None:
            continue
        row["status"] = "done"
        row["adjudicated_gold_sections"] = _sort_sections(adj["gold_sections"])
        row["adjudicated_parse_quality"] = adj["parse_quality"]
        row["adjudicated_resume_quality"] = adj["resume_quality"]
        row["adjudicated_issue_types"] = _sort_issues(adj["issue_types"])
        row["adjudicator"] = ADJUDICATOR
        row["adjudicated_at"] = adjudicated_at
        row["rationale"] = adj["rationale"]

    worksheet["pending"] = 0
    worksheet["done"] = len(worksheet["cases"])
    worksheet["adjudicated_at"] = adjudicated_at
    WORKSHEET.write_text(json.dumps(worksheet, ensure_ascii=False, indent=2), encoding="utf-8")

    gold_cases = []
    for case_id in CASE_IDS:
        adj = ADJUDICATIONS[case_id]
        a_case = annot_a_map[case_id]
        txt_path = DATASET / f"{case_id}.txt"
        text = txt_path.read_text(encoding="utf-8") if txt_path.exists() else a_case.get("text", "")
        gold_cases.append(
            {
                "id": case_id,
                "text": text,
                "gold_sections": _sort_sections(adj["gold_sections"]),
                "parse_quality": adj["parse_quality"],
                "resume_quality": adj["resume_quality"],
                "issue_types": _sort_issues(adj["issue_types"]),
                "annotator_a": "A",
                "annotator_b": "B",
                "adjudicated_by": ADJUDICATOR,
                "notes": adj["rationale"],
            }
        )

    gold_payload = {
        "version": 1,
        "label_policy": "two_annotator_adjudicated_common15",
        "adjudicated_at": adjudicated_at,
        "adjudicator": ADJUDICATOR,
        "source_disagreements": "docs/testing/annotation_disagreements_A_B_common15.json",
        "cases": gold_cases,
    }
    GOLD_OUT.parent.mkdir(parents=True, exist_ok=True)
    GOLD_OUT.write_text(json.dumps(gold_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "worksheet": str(WORKSHEET),
                "gold": str(GOLD_OUT),
                "cases": len(gold_cases),
                "done": worksheet["done"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
