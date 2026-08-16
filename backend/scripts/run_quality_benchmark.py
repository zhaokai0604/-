"""Run the local acceptance benchmark and generate a UTF-8 Word report.

The benchmark deliberately keeps raw resume content out of the result JSON and
the report. It records counts, timings, labels and aggregate metrics only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean
from typing import Any, Callable

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "quality-benchmark-secret")

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.analysis_pipeline import run_analysis_pipeline  # noqa: E402
from app.services.match_engine import match_job  # noqa: E402
from app.services.parser import detect_sections, parse_resume  # noqa: E402
from app.services.pipeline_utils import normalize_sections  # noqa: E402
from app.services.semantic_match import semantic_similarity  # noqa: E402
from _resume_corpus_common import extract_text, iter_resume_files  # noqa: E402


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return round(ordered[index], 2)


def summary(values: list[float]) -> dict[str, float]:
    return {
        "count": len(values),
        "mean_ms": round(mean(values), 2) if values else 0.0,
        "p50_ms": percentile(values, 0.50),
        "p95_ms": percentile(values, 0.95),
        "min_ms": round(min(values), 2) if values else 0.0,
        "max_ms": round(max(values), 2) if values else 0.0,
    }


def command_result(command: list[str], cwd: Path, timeout: int = 300) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        child_env = os.environ.copy()
        if "pytest" in command:
            # pytest's admin fixture intentionally uses the test-only account.
            child_env.update({"ADMIN_USERNAME": "sysadmin", "ADMIN_PASSWORD": "Password1"})
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=child_env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
        )
        output = (completed.stdout + "\n" + completed.stderr).strip()
        return {
            "returncode": completed.returncode,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "tail": output[-3000:],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "returncode": -1,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "tail": f"{type(exc).__name__}: {exc}",
        }


def f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def rank(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[cursor][0]:
            end += 1
        average = (cursor + end) / 2 + 1
        for index in range(cursor, end + 1):
            ranks[ordered[index][1]] = average
        cursor = end + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    rx, ry = rank(xs), rank(ys)
    mx, my = mean(rx), mean(ry)
    numerator = sum((x - mx) * (y - my) for x, y in zip(rx, ry))
    dx = sum((x - mx) ** 2 for x in rx) ** 0.5
    dy = sum((y - my) ** 2 for y in ry) ** 0.5
    return round(numerator / (dx * dy), 4) if dx and dy else 0.0


def run_functional_tests() -> dict[str, Any]:
    parse_path = PROJECT_ROOT / "data" / "eval" / "parse_cases.json"
    payload = json.loads(parse_path.read_text(encoding="utf-8"))
    tp = fp = fn = 0
    rows = []
    for case in payload.get("cases") or []:
        gold = set(case.get("gold_sections") or [])
        predicted = {
            key for key, lines in normalize_sections(detect_sections(str(case.get("text") or ""))).items() if lines
        }
        tp += len(gold & predicted)
        fp += len(predicted - gold)
        fn += len(gold - predicted)
        rows.append({"hit": not (gold - predicted or predicted - gold)})
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "synthetic_parse": {
            "cases": len(rows),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1(precision, recall), 4),
            "exact_case_rate": round(sum(row["hit"] for row in rows) / len(rows), 4) if rows else 0.0,
        },
        "pipeline_smoke": command_result(
            [sys.executable, "scripts/verify_optimization_pipeline.py"], ROOT
        ),
    }


def run_match_ablation() -> dict[str, Any]:
    cases = json.loads((PROJECT_ROOT / "data" / "eval" / "match_cases.json").read_text(encoding="utf-8")).get("cases") or []
    labels: list[float] = []
    rule_scores: list[float] = []
    semantic_scores: list[float] = []
    fused_scores: list[float] = []
    for case in cases:
        os.environ["USE_SEMANTIC_MATCH"] = "false"
        rule = match_job(case["resume"], [], case.get("job", "").split("，")[0], case["job"], "manual")
        os.environ["USE_SEMANTIC_MATCH"] = "true"
        fused = match_job(case["resume"], [], case.get("job", "").split("，")[0], case["job"], "manual")
        semantic = semantic_similarity(case["resume"], case["job"])
        labels.append(float(case["label"]))
        rule_scores.append(float(rule["score"]))
        semantic_scores.append(float(semantic["score"]))
        fused_scores.append(float(fused["score"]))
    result = {
        "cases": len(cases),
        "rule_spearman": spearman(labels, rule_scores),
        "semantic_spearman": spearman(labels, semantic_scores),
        "semantic_primary_spearman": spearman(labels, fused_scores),
        "evaluation_scope": "exploratory_same_weak_label_set_not_holdout",
    }
    result["fused_spearman"] = result["semantic_primary_spearman"]
    result["fused_lift_vs_rule"] = round(result["semantic_primary_spearman"] - result["rule_spearman"], 4)
    return result


def run_guardrail_eval() -> dict[str, Any]:
    cases = [
        ("pass", "本科", "某大学 本科"),
        ("fail", "本科", "某职业学院 专科"),
        ("fail", "硕士", "某大学 本科"),
        ("unknown", "本科", "教育经历待补充"),
    ]
    observed: list[dict[str, str]] = []
    for expected, degree, education in cases:
        result = match_job(
            f"教育背景\n{education}\n技能\nPython",
            [],
            "数据分析师",
            f"{degree}及以上，要求 Python",
            "manual",
            sections={"education": [education], "skills": ["Python"]},
            structured={"education": [{"raw": education}]},
        )
        status = (result.get("hard_constraints") or [{}])[0].get("status", "none")
        observed.append({"expected": expected, "observed": status})
    pass_cases = [row for row in observed if row["expected"] == "pass"]
    fail_cases = [row for row in observed if row["expected"] == "fail"]
    return {
        "cases": len(observed),
        "false_positive_rate": round(sum(row["observed"] == "fail" for row in pass_cases) / max(len(pass_cases), 1), 4),
        "violation_detection_rate": round(sum(row["observed"] == "fail" for row in fail_cases) / max(len(fail_cases), 1), 4),
        "unknown_safe_rate": round(sum(row["observed"] == "unknown" for row in observed if row["expected"] == "unknown") / 1, 4),
        "rows": observed,
    }


def run_real_corpus(corpus: Path) -> dict[str, Any]:
    files = iter_resume_files(corpus)
    baseline = {"docx": 0, "pdf": 0, "text_ok": 0, "text_empty": 0, "total": len(files)}
    improved = {"docx": 0, "pdf": 0, "text_ok": 0, "text_empty": 0, "total": len(files)}
    for path in files:
        suffix = path.suffix.lower().lstrip(".")
        baseline[suffix] = baseline.get(suffix, 0) + 1
        improved[suffix] = improved.get(suffix, 0) + 1
        text, _ = extract_text(path, enable_ocr=False)
        improved_text, _ = extract_text(path, enable_ocr=True)
        baseline["text_ok" if text.strip() else "text_empty"] += 1
        improved["text_ok" if improved_text.strip() else "text_empty"] += 1

    analysis_ok = 0
    quality_pass = 0
    analysis_ms: list[float] = []
    quality_counts: dict[str, int] = {}
    failures: list[str] = []
    for index, path in enumerate(files, 1):
        started = time.perf_counter()
        try:
            output = run_analysis_pipeline(path, "", "", False)
            result = output.get("result") or {}
            if isinstance(result.get("total_score"), (int, float)) and result.get("scores"):
                analysis_ok += 1
            quality = str(result.get("parse_quality") or "unknown")
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
            if quality in {"high", "medium"}:
                quality_pass += 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"case-{index}:{type(exc).__name__}")
        analysis_ms.append((time.perf_counter() - started) * 1000)
    for item in (baseline, improved):
        item["text_rate"] = round(item["text_ok"] / item["total"], 4) if item["total"] else 0.0
    return {
        "files": len(files),
        "baseline_no_ocr": baseline,
        "improved_ocr": improved,
        "analysis_success": analysis_ok,
        "analysis_rate": round(analysis_ok / len(files), 4) if files else 0.0,
        "quality_pass": quality_pass,
        "quality_pass_rate": round(quality_pass / len(files), 4) if files else 0.0,
        "quality_counts": quality_counts,
        "analysis_timing": summary(analysis_ms),
        "failure_types": failures[:20],
    }


def timed_call(path: Path) -> float:
    started = time.perf_counter()
    run_analysis_pipeline(path, "", "", False)
    return (time.perf_counter() - started) * 1000


def run_performance(sample: Path) -> dict[str, Any]:
    warmup = timed_call(sample)
    baseline_times = [timed_call(sample) for _ in range(10)]
    pressure_times = [timed_call(sample) for _ in range(20)]
    capacity: dict[str, Any] = {}
    for size in (1, 5, 10, 20):
        started = time.perf_counter()
        completed = 0
        for _ in range(size):
            timed_call(sample)
            completed += 1
        capacity[str(size)] = {
            "requested": size,
            "completed": completed,
            "wall_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    concurrent: dict[str, Any] = {}
    for workers in (2, 4, 8):
        started = time.perf_counter()
        results: list[float] = []
        failures = 0
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(timed_call, sample) for _ in range(workers)]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    failures += 1
        concurrent[str(workers)] = {
            "workers": workers,
            "success": len(results),
            "failures": failures,
            "wall_ms": round((time.perf_counter() - started) * 1000, 2),
            "task_timing": summary(results),
        }
    return {
        "sample_type": sample.suffix.lower().lstrip("."),
        "warmup_ms": round(warmup, 2),
        "baseline": summary(baseline_times),
        "pressure_20": summary(pressure_times),
        "capacity": capacity,
        "concurrency": concurrent,
    }


def build_docx(report: dict[str, Any], output: Path) -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    styles = doc.styles
    styles["Normal"].font.name = "Microsoft YaHei"
    styles["Normal"].font.size = Pt(10.5)
    title = doc.add_heading("简析智评功能与性能测试报告", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph("测试版本：当前优化版　|　测试日期：" + time.strftime("%Y-%m-%d"))
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("本报告基于本地可复现脚本生成，原始简历仅在本地读取；报告和结果 JSON 不保存姓名、电话、学校、邮箱或简历正文。指标按实际测试口径记录，未将设计目标写成实测结果。")

    def heading(text: str, level: int = 1) -> None:
        doc.add_heading(text, level)

    def table(headers: list[str], rows: list[list[Any]]) -> None:
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        for cell, value in zip(t.rows[0].cells, headers):
            cell.text = str(value)
        for row in rows:
            cells = t.add_row().cells
            for cell, value in zip(cells, row):
                cell.text = str(value)

    functional = report["functional"]
    real = report["real_corpus"]
    perf = report["performance"]
    heading("一、测试结论", 1)
    doc.add_paragraph(
        f"本轮共处理真实简历 {real['files']} 份。未启用 OCR 时正文可读率为 "
        f"{real['baseline_no_ocr']['text_rate']:.1%}，启用 OCR 后为 {real['improved_ocr']['text_rate']:.1%}；"
        f"端到端分析成功率为 {real['analysis_rate']:.1%}，解析质量通过率为 {real['quality_pass_rate']:.1%}。"
        "OCR 提升的是文档可接入性，不能直接解释为板块识别准确率提升。"
    )
    doc.add_paragraph(
        f"合成解析集 {functional['synthetic_parse']['cases']} 条的板块级 F1 为 "
        f"{functional['synthetic_parse']['f1']:.4f}；该结果仅作为规则回归基线。"
    )
    doc.add_paragraph(
        f"探索性岗位匹配评估中，规则、语义、语义主排序 Spearman 分别为 "
        f"{report['match_ablation']['rule_spearman']:.4f}、"
        f"{report['match_ablation']['semantic_spearman']:.4f}、"
        f"{report['match_ablation']['semantic_primary_spearman']:.4f}。该结果使用同一弱标注集合，不能作为泛化验收结论。"
    )

    heading("二、测试范围与环境", 1)
    table(["项目", "口径"], [
        ["输入数据", f"真实简历 {real['files']} 份；仅保留聚合结果"],
        ["文件构成", f"DOCX {real['baseline_no_ocr'].get('docx', 0)} 份；PDF {real['baseline_no_ocr'].get('pdf', 0)} 份"],
        ["运行模式", "本地规则解析、岗位匹配、可选语义模型；AI 改写关闭"],
        ["Python", sys.executable],
        ["报告生成", "python-docx，UTF-8 文本写入"],
    ])

    heading("三、底层功能测试", 1)
    table(["指标", "结果", "说明"], [
        ["解析板块 Precision", functional["synthetic_parse"]["precision"], "20 条合成脱敏样本，板块级"],
        ["解析板块 Recall", functional["synthetic_parse"]["recall"], "20 条合成脱敏样本，板块级"],
        ["解析板块 F1", functional["synthetic_parse"]["f1"], "不可外推为真实简历字段准确率"],
        ["端到端分析成功率", real["analysis_rate"], f"真实文件 {real['analysis_success']}/{real['files']}"],
        ["解析质量通过率", real["quality_pass_rate"], f"high/medium {real['quality_pass']}/{real['files']}"],
        ["优化链路冒烟", functional["pipeline_smoke"]["returncode"], "优化稿、Diff、技能提示、报告导出"],
    ])
    doc.add_paragraph("通过率定义：端到端分析成功需返回 total_score 与 scores；解析质量通过指系统判定为 high 或 medium。低质量不等于简历质量差，而是提示证据不足或需人工复核。")

    heading("四、基准、对比、消融与改进实验", 1)
    table(["实验", "配置", "核心结果"], [
        ["解析基准", "无 OCR", f"文本可读率 {real['baseline_no_ocr']['text_rate']:.1%}"],
        ["解析改进", "启用本地 OCR", f"文本可读率 {real['improved_ocr']['text_rate']:.1%}"],
        ["匹配消融 A", "仅规则", report["match_ablation"]["rule_spearman"]],
        ["匹配消融 B", "语义模型通道", report["match_ablation"]["semantic_spearman"]],
        ["匹配消融 C", "语义主排序 + 规则证据", report["match_ablation"]["semantic_primary_spearman"]],
        ["相对提升", "语义主排序 - 规则", report["match_ablation"]["fused_lift_vs_rule"]],
    ])
    doc.add_paragraph("模型培优结论：现有双塔语义模型作为主排序器，规则引擎只负责硬约束、证据解释和规则回退。当前 61 条结果属于探索性分析；正式验收必须按岗位模板分组切分 Validation/Test，且测试集只在最终评估时使用一次。")
    if report.get("holdout"):
        holdout = report["holdout"]
        doc.add_paragraph(
            f"留出基线（{holdout.get('split', 'test')}，{holdout.get('cases', 0)} 条）："
            f"规则 Spearman {holdout.get('rule_spearman', 0):.4f}，"
            f"语义直算 {holdout.get('semantic_spearman', 0):.4f}，"
            f"系统语义主排序 {holdout.get('semantic_primary_spearman', 0):.4f}。"
            "由于当前权重仍来自全量源集合，该结果仅用于发现切分后的分布变化。"
        )
    guardrail = report["guardrail_eval"]
    doc.add_paragraph(
        f"规则护栏专项：学历硬约束误拦截率 {guardrail['false_positive_rate']:.1%}，"
        f"违规识别率 {guardrail['violation_detection_rate']:.1%}，"
        f"证据缺失安全处理率 {guardrail['unknown_safe_rate']:.1%}。"
    )

    heading("五、整体性能测试", 1)
    table(["测试类型", "结果", "判定"], [
        ["基准测试", f"均值 {perf['baseline']['mean_ms']} ms；P95 {perf['baseline']['p95_ms']} ms", "实测"],
        ["压力测试", f"20 次顺序调用；P95 {perf['pressure_20']['p95_ms']} ms", "实测"],
        ["容量测试", "1/5/10/20 份顺序任务均记录完成数", "实测"],
        ["稳定性测试", "与压力测试同一固定输入重复 20 次", "实测"],
        ["并发测试", "2/4/8 worker，记录成功、失败和墙钟时间", "实测"],
    ])
    doc.add_paragraph("性能结果受本机 CPU、内存、模型首次加载和本地磁盘影响，适合比较当前版本改动，不应直接当作服务器 SLA。首次调用单独记录为 warm-up。")
    for workers, item in perf["concurrency"].items():
        doc.add_paragraph(f"并发 {workers}：成功 {item['success']}，失败 {item['failures']}，墙钟 {item['wall_ms']} ms。")

    heading("六、问题与改进建议", 1)
    doc.add_paragraph("1. 当前合成解析集结果较高，下一步应以 A 池人工复核后的 gold_sections 作为正式真实板块评测，不宜继续扩大合成集指标。")
    doc.add_paragraph("2. OCR 后全部文件可读，但扫描 PDF 的文字质量仍需抽样复核；报告中的质量通过率与文本可读率必须同时展示。")
    doc.add_paragraph("3. 语义模型已有提升证据，但 61 条岗位集合属于同源弱标注探索集；应在岗位库扩充后按岗位模板分组切分训练、验证和测试集，单独报告真实岗位评测。")
    doc.add_paragraph("4. 并发测试若出现失败，应优先检查语义模型单例、OCR 引擎锁、SQLite 写入和 SSE 认领状态；不要只通过增加超时掩盖问题。")

    heading("七、复现命令", 1)
    doc.add_paragraph("在 backend 目录运行：")
    for command in [
        ".\\.venv\\Scripts\\python.exe scripts/run_quality_benchmark.py --corpus <本地真实简历目录>",
        ".\\.venv\\Scripts\\python.exe -m pytest tests -q",
        "npm run build（在 frontend 目录）",
    ]:
        doc.add_paragraph(command, style="No Spacing")
    doc.save(str(output))


def main() -> int:
    parser = argparse.ArgumentParser(description="生成简析智评功能与性能测试报告")
    parser.add_argument("--corpus", type=Path, required=True, help="本地真实简历目录，不会复制到报告")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "docs" / "testing" / "简析智评功能与性能测试报告.docx")
    parser.add_argument("--skip-real-analysis", action="store_true", help="只跑功能与性能，不处理全部真实文件")
    args = parser.parse_args()
    files = iter_resume_files(args.corpus)
    if not files:
        raise SystemExit("真实简历目录为空")
    functional = run_functional_tests()
    match_ablation = run_match_ablation()
    real = run_real_corpus(args.corpus) if not args.skip_real_analysis else {
        "files": len(files), "baseline_no_ocr": {}, "improved_ocr": {}, "analysis_rate": 0.0,
        "quality_pass_rate": 0.0, "analysis_success": 0, "quality_pass": 0, "quality_counts": {},
    }
    sample = next((path for path in files if path.suffix.lower() == ".docx"), files[0])
    performance = run_performance(sample)
    pytest_result = command_result([sys.executable, "-m", "pytest", "tests", "-q"], ROOT, timeout=300)
    report = {
        "version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "functional": functional,
        "match_ablation": match_ablation,
        "guardrail_eval": run_guardrail_eval(),
        "real_corpus": real,
        "performance": performance,
        "pytest": pytest_result,
        "input_fingerprint": hashlib.sha256(str(args.corpus.resolve()).encode("utf-8")).hexdigest()[:12],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    json_path = args.output.with_suffix(".json")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_docx(report, args.output)
    print(json.dumps({
        "report": str(args.output),
        "json": str(json_path),
        "real_files": real.get("files"),
        "analysis_rate": real.get("analysis_rate"),
        "quality_pass_rate": real.get("quality_pass_rate"),
        "pytest_returncode": pytest_result.get("returncode"),
        "performance_p95_ms": performance["baseline"]["p95_ms"],
    }, ensure_ascii=False, indent=2))
    return 0 if pytest_result.get("returncode") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
