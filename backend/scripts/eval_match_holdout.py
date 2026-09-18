"""Evaluate the group-held-out match split without hiding leakage status."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "holdout-eval-secret")
os.environ.setdefault("USE_SEMANTIC_MATCH", "true")

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from eval_match_baseline import spearman  # noqa: E402

from app.services.match_engine import match_job  # noqa: E402
from app.services.semantic_match import clear_semantic_caches, semantic_similarity  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="评估岗位匹配组间留出集")
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "data" / "eval" / "match_splits")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument("--idf-path", type=Path, default=None)
    args = parser.parse_args()
    if args.model_path:
        os.environ["SEMANTIC_MODEL_PATH"] = str(args.model_path.resolve())
    if args.idf_path:
        os.environ["SEMANTIC_IDF_PATH"] = str(args.idf_path.resolve())
    clear_semantic_caches()
    payload = json.loads((args.input_dir / f"{args.split}.json").read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    labels: list[float] = []
    rule_scores: list[float] = []
    semantic_scores: list[float] = []
    primary_scores: list[float] = []
    for case in cases:
        job = str(case.get("job") or "")
        position = job.split("，", 1)[0]
        os.environ["USE_SEMANTIC_MATCH"] = "false"
        rule = match_job(case["resume"], [], position, job, "manual")
        os.environ["USE_SEMANTIC_MATCH"] = "true"
        primary = match_job(case["resume"], [], position, job, "manual")
        semantic = semantic_similarity(case["resume"], job)
        labels.append(float(case["label"]))
        rule_scores.append(float(rule["score"]))
        semantic_scores.append(float(semantic["score"]))
        primary_scores.append(float(primary["score"]))

    training_status = (
        "strict train-only IDF baseline; no SBERT fine-tuning was applied"
        if not os.getenv("USE_SEMANTIC_MODEL", "false").lower() == "true"
        else "current transformer weights were trained/fitted on the full 61-case source; leakage-aware baseline only"
    )
    result = {
        "split": args.split,
        "cases": len(cases),
        "groups_are_disjoint": True,
        "model_training_status": training_status,
        "rule_spearman": spearman(labels, rule_scores),
        "semantic_spearman": spearman(labels, semantic_scores),
        "semantic_primary_spearman": spearman(labels, primary_scores),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
