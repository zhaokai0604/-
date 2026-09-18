"""Run platform-only acceptance tests without model fitting or weak-label ablations."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _resume_corpus_common import extract_text, iter_resume_files  # noqa: E402
from run_quality_benchmark import (  # noqa: E402
    run_functional_tests,
    run_guardrail_eval,
    run_performance,
)

from app.services.analysis_pipeline import run_analysis_pipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="生成不含模型拟合/弱标注消融的平台验收结果")
    parser.add_argument("--corpus", type=Path, required=True, help="脱敏本地样本目录")
    parser.add_argument("--output", type=Path, required=True, help="UTF-8 JSON 输出路径")
    parser.add_argument("--no-ocr", action="store_true", help="只测原生文本抽取，作为 OCR 前基线")
    args = parser.parse_args()

    files = [path for path in iter_resume_files(args.corpus) if path.suffix.lower() in {".docx", ".pdf"}]
    if not files:
        raise SystemExit("样本目录为空")

    started = time.perf_counter()
    functional = run_functional_tests()
    guardrail = run_guardrail_eval()
    real = run_document_corpus(files, enable_ocr=not args.no_ocr)
    performance = run_performance(files[0])
    report = {
        "version": 1,
        "experiment": "platform_acceptance_only",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "corpus_files": len(files),
        "corpus_scope": "本地离线只读文档；只写出聚合指标，不进入平台业务数据、不用于模型训练",
        "model_policy": "frozen_inference_only_no_fit_no_alpha",
        "functional": functional,
        "guardrail": guardrail,
        "real_corpus": real,
        "performance": performance,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "excluded": ["match_cases.json", "train_sbert.py", "train_biencoder.py", "alpha fitting"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "corpus_files": report["corpus_files"],
        "analysis_rate": real.get("analysis_rate"),
        "text_rate_no_ocr": real.get("baseline_no_ocr", {}).get("text_rate"),
        "text_rate_ocr": real.get("improved_ocr", {}).get("text_rate"),
        "guardrail": guardrail,
        "duration_ms": report["duration_ms"],
    }, ensure_ascii=False, indent=2))
    return 0


def run_document_corpus(files: list[Path], *, enable_ocr: bool) -> dict:
    baseline = {"docx": 0, "pdf": 0, "text_ok": 0, "text_empty": 0, "total": len(files)}
    improved = {"docx": 0, "pdf": 0, "text_ok": 0, "text_empty": 0, "total": len(files)}
    for path in files:
        suffix = path.suffix.lower().lstrip(".")
        baseline[suffix] += 1
        improved[suffix] += 1
        text, _ = extract_text(path, enable_ocr=False)
        improved_text, _ = extract_text(path, enable_ocr=enable_ocr)
        baseline["text_ok" if text.strip() else "text_empty"] += 1
        improved["text_ok" if improved_text.strip() else "text_empty"] += 1

    analysis_ok = 0
    quality_pass = 0
    quality_counts: dict[str, int] = {}
    failures: list[str] = []
    timings: list[float] = []
    for index, path in enumerate(files, 1):
        started = time.perf_counter()
        try:
            result = (run_analysis_pipeline(path, "", "", False).get("result") or {})
            if isinstance(result.get("total_score"), int | float) and result.get("scores"):
                analysis_ok += 1
            quality = str(result.get("parse_quality") or "unknown")
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
            if quality in {"high", "medium"}:
                quality_pass += 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"case-{index}:{type(exc).__name__}")
        timings.append((time.perf_counter() - started) * 1000)

    def rate(value: int) -> float:
        return round(value / len(files), 4) if files else 0.0

    for item in (baseline, improved):
        item["text_rate"] = rate(item["text_ok"])
    ordered = sorted(timings)
    p95 = ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))] if ordered else 0.0
    return {
        "files": len(files),
        "baseline_no_ocr": baseline,
        "improved_ocr": improved,
        "analysis_success": analysis_ok,
        "analysis_rate": rate(analysis_ok),
        "quality_pass": quality_pass,
        "quality_pass_rate": rate(quality_pass),
        "quality_counts": quality_counts,
        "analysis_timing": {"count": len(timings), "p95_ms": round(p95, 2)},
        "failure_types": failures[:20],
    }


if __name__ == "__main__":
    raise SystemExit(main())
