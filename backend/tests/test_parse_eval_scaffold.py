"""解析评测脚手架冒烟。"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.parser import detect_sections
from app.services.pipeline_utils import normalize_sections


def test_parse_cases_exist_and_detect_sections():
    root = Path(__file__).resolve().parents[2]
    path = root / "data" / "eval" / "parse_cases.json"
    assert path.exists()
    cases = json.loads(path.read_text(encoding="utf-8")).get("cases") or []
    assert len(cases) >= 15
    sample = next(case for case in cases if case["id"] == "std-da")
    sections = normalize_sections(detect_sections(sample["text"]))
    predicted = {key for key, lines in sections.items() if lines}
    assert "skills" in predicted
    assert "internship" in predicted or "projects" in predicted


def test_parse_baseline_artifact_optional():
    root = Path(__file__).resolve().parents[2]
    path = root / "data" / "eval" / "parse_baseline_last.json"
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "micro_f1" in payload
    assert 0.0 <= float(payload["micro_f1"]) <= 1.0
