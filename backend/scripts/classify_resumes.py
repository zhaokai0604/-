"""脱敏简历智能分拣：A（解析评测）/ B（Bad Case）/ C（演示备用）。

默认读取: data/anonymized_real_resumes/*.txt
输出:
  data/resume_pools/
    pool_A/ pool_B/ pool_C/     （复制 txt，可选 docx）
    classify_report.json
    pool_summary.md

规则（可调阈值）:
  - layout_complexity: 行数、短行密度、表格分隔符、碎片行
  - has_intent: 求职意向/目标岗位等
  - has_numbers: 量化词与数字量词
  - section_signal: 能否检出多板块（调用本仓库 detect_sections）

硬约束:
  - C 池仅演示，不进训练集
  - 不调用大模型打匹配分
  - 不自动写入 train_sbert / match_cases

用法:
  cd backend
  .\\.venv\\Scripts\\python.exe scripts\\classify_resumes.py
  .\\.venv\\Scripts\\python.exe scripts\\classify_resumes.py --a-size 15 --b-size 10
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "classify-resume-secret")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _resume_corpus_common import (  # noqa: E402
    default_anon_dir,
    default_pools_dir,
    ensure_dir,
    extract_text,
    iter_resume_files,
    safe_stem,
    write_json,
)

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.services.parser import detect_sections, detect_target_position  # noqa: E402

INTENT_RE = re.compile(
    r"(求职意向|意向岗位|目标岗位|应聘岗位|应聘职位|期望岗位|求职方向|目标职位|Desired\s*Position|Objective)",
    re.I,
)
NUMBER_METRIC_RE = re.compile(
    r"(\d+(?:\.\d+)?\s*%|\d+\s*\+|(\d+)\s*(人|次|个|项|篇|条|万|w|W|k|K)|提升|下降|增长|完成\s*\d)",
    re.I,
)
TABLE_HINT_RE = re.compile(r"\s\|\s|｜|\t")
SHORT_FRAG_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9]{1,2}$")


def score_layout(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    n = max(len(lines), 1)
    short_ratio = sum(1 for ln in lines if len(ln) <= 4 or SHORT_FRAG_RE.match(ln)) / n
    table_lines = sum(1 for ln in lines if TABLE_HINT_RE.search(ln))
    avg_len = sum(len(ln) for ln in lines) / n
    # 换行密度：字符数 / 行数 越小越碎
    density = len(text) / n
    complexity = 0.0
    if n >= 40:
        complexity += 1.2
    elif n >= 25:
        complexity += 0.7
    if short_ratio >= 0.35:
        complexity += 1.3
    elif short_ratio >= 0.2:
        complexity += 0.6
    if table_lines >= 6:
        complexity += 1.4
    elif table_lines >= 2:
        complexity += 0.7
    if avg_len < 12:
        complexity += 0.8
    if density < 18:
        complexity += 0.5
    # 超长单行也可能是版式粘连
    long_sticky = sum(1 for ln in lines if len(ln) > 120)
    if long_sticky >= 3:
        complexity += 0.9
    return {
        "line_count": len(lines),
        "short_ratio": round(short_ratio, 3),
        "table_like_lines": table_lines,
        "avg_line_len": round(avg_len, 2),
        "char_per_line": round(density, 2),
        "long_sticky_lines": long_sticky,
        "layout_complexity": round(complexity, 3),
    }


def score_content(text: str) -> dict[str, Any]:
    sections = detect_sections(text)
    non_empty = sorted(k for k, v in sections.items() if v)
    intent = bool(INTENT_RE.search(text) or detect_target_position(text, sections))
    metrics = NUMBER_METRIC_RE.findall(text)
    # findall 可能返回元组
    metric_count = len(metrics)
    rich_sections = sum(1 for k in ("education", "internship", "projects", "skills", "campus", "awards") if sections.get(k))
    quality = 0.0
    quality += min(rich_sections, 5) * 0.9
    quality += min(metric_count, 8) * 0.35
    if intent:
        quality += 0.6
    if len(text) >= 400:
        quality += 0.5
    if len(text) >= 800:
        quality += 0.4
    # 正文太短直接降质
    if len(text.strip()) < 120:
        quality -= 2.0
    return {
        "has_intent": intent,
        "metric_count": metric_count,
        "section_keys": non_empty,
        "rich_section_count": rich_sections,
        "content_quality": round(quality, 3),
        "detected_target": detect_target_position(text, sections) or "",
    }


def classify_one(path: Path) -> dict[str, Any]:
    text, warnings = extract_text(path)
    layout = score_layout(text)
    content = score_content(text)
    # 综合分：高 content + 低 complexity → A；高 complexity → B
    a_score = content["content_quality"] - layout["layout_complexity"] * 0.85
    if content["has_intent"]:
        a_score += 0.3
    b_score = layout["layout_complexity"] + (1.2 if len(text.strip()) < 80 else 0.0)
    if "扫描" in " ".join(warnings) or "OCR" in " ".join(warnings) or "过短" in " ".join(warnings):
        b_score += 1.0
    return {
        "file": path.name,
        "stem": safe_stem(path),
        "path": str(path),
        "chars": len(text),
        "source_type": path.suffix.lower().lstrip("."),
        "text_length": len(text.strip()),
        "extract_status": "ok" if text.strip() else "empty_or_unreadable",
        "ocr_used": False,
        "extract_warnings": warnings,
        **layout,
        **content,
        "a_score": round(a_score, 3),
        "b_score": round(b_score, 3),
        "pool": "",  # 稍后填充
    }


def assign_pools(rows: list[dict[str, Any]], a_size: int, b_size: int) -> list[dict[str, Any]]:
    if not rows:
        return rows
    # B：复杂度优先
    by_b = sorted(rows, key=lambda r: (r["b_score"], r["layout_complexity"], -r["chars"]), reverse=True)
    b_ids = {id(r) for r in by_b[: max(0, b_size)]}
    # A：从非 B 中按 a_score
    remain = [r for r in rows if id(r) not in b_ids]
    by_a = sorted(
        remain,
        key=lambda r: (r["a_score"], r["rich_section_count"], r["metric_count"], r["chars"]),
        reverse=True,
    )
    a_ids = {id(r) for r in by_a[: max(0, a_size)]}
    for r in rows:
        if id(r) in b_ids:
            r["pool"] = "B"
        elif id(r) in a_ids:
            r["pool"] = "A"
        else:
            r["pool"] = "C"
    return rows


def materialize_pools(rows: list[dict[str, Any]], pools_dir: Path, anon_dir: Path) -> None:
    for name in ("pool_A", "pool_B", "pool_C"):
        ensure_dir(pools_dir / name)
        # 清空旧复制（只删文件不删目录）
        for old in (pools_dir / name).glob("*"):
            if old.is_file() and old.name != ".gitkeep":
                old.unlink()

    for r in rows:
        pool = r["pool"]
        src = Path(r["path"])
        dst_dir = pools_dir / f"pool_{pool}"
        shutil.copy2(src, dst_dir / src.name)
        # 若有同名 docx 一并带上
        docx = anon_dir / f"{r['stem']}.docx"
        if docx.exists():
            shutil.copy2(docx, dst_dir / docx.name)


def write_summary_md(path: Path, rows: list[dict[str, Any]], a_size: int, b_size: int) -> None:
    lines = [
        "# 真实简历分拣结果",
        "",
        f"- A 池目标约 {a_size}：结构清晰 + 量化较多 → **解析评测**（需人工标 gold_sections）",
        f"- B 池目标约 {b_size}：版式复杂/碎片多 → **Bad Case / 能力边界**",
        "- C 池：其余 → **仅现场演示，禁止进训练集**",
        "",
        "## 分布",
        "",
    ]
    for pool in ("A", "B", "C"):
        subset = [r for r in rows if r["pool"] == pool]
        lines.append(f"### {pool} 池（{len(subset)}）")
        lines.append("")
        lines.append("| 文件 | 来源 | 提取状态 | a_score | b_score | 板块数 | 量化 | 意向 | 复杂度 |")
        lines.append("|---|---|---|---:|---:|---:|---:|---|---:|")
        for r in subset:
            lines.append(
                f"| {r['file']} | {r.get('source_type', '-')} | {r.get('extract_status', '-')} | "
                f"{r['a_score']} | {r['b_score']} | {r['rich_section_count']} | "
                f"{r['metric_count']} | {'Y' if r['has_intent'] else 'N'} | {r['layout_complexity']} |"
            )
        lines.append("")
    lines.extend(
        [
            "## 人工必做",
            "",
            "1. 抽查 A/B 各 3 份，确认分池合理，不合理则改 `classify_report.json` 的 pool 字段后重跑 `--from-report`",
            "2. A 池人工标注 `gold_sections` 后再接入 `eval_parse_baseline.py`",
            "3. C 池固定挑 2～3 份作为上场演示名单",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="脱敏简历 A/B/C 分拣")
    parser.add_argument("--input", type=Path, default=default_anon_dir())
    parser.add_argument("--output", type=Path, default=default_pools_dir())
    parser.add_argument("--a-size", type=int, default=15)
    parser.add_argument("--b-size", type=int, default=10)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="脱敏报告路径，用于把原始格式、OCR 和提取状态带入分池报告",
    )
    parser.add_argument(
        "--from-report",
        type=Path,
        default=None,
        help="基于已有 classify_report.json 只重新落盘复制（便于人工改 pool）",
    )
    args = parser.parse_args()

    print("=== classify_resumes ===")
    if args.from_report and args.from_report.exists():
        import json

        payload = json.loads(args.from_report.read_text(encoding="utf-8"))
        rows = payload.get("rows") or []
        print(f"reload {len(rows)} rows from {args.from_report}")
    else:
        files = [p for p in iter_resume_files(args.input) if p.suffix.lower() in {".txt", ".md", ".docx", ".pdf"}]
        # 优先 txt（脱敏权威）
        txts = [p for p in files if p.suffix.lower() == ".txt"]
        files = txts or files
        if args.limit > 0:
            files = files[: args.limit]
        print(f"input: {args.input} ({len(files)} files)")
        if not files:
            print("未找到脱敏简历，请先运行 anonymize_resumes.py")
            return 1
        rows = [classify_one(p) for p in files]
        manifest_path = args.manifest or (args.input / "anonymize_report.json")
        if manifest_path.exists():
            import json

            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            metadata = {str(item.get("stem")): item for item in payload.get("rows") or []}
            for row in rows:
                meta = metadata.get(row.get("stem"), {})
                for key in ("source_type", "text_length", "ocr_used", "extract_status", "extract_warnings"):
                    if key in meta:
                        row[key] = meta[key]
        rows = assign_pools(rows, args.a_size, args.b_size)

    ensure_dir(args.output)
    materialize_pools(rows, args.output, args.input)
    counts = {k: sum(1 for r in rows if r["pool"] == k) for k in ("A", "B", "C")}
    report = {
        "cases": len(rows),
        "counts": counts,
        "a_size_target": args.a_size,
        "b_size_target": args.b_size,
        "input": str(args.input),
        "output": str(args.output),
        "rows": rows,
        "policy": {
            "pool_C": "demo_only_never_train",
            "forbidden": ["llm_match_labeling", "auto_append_match_cases", "auto_train_sbert"],
        },
    }
    write_json(args.output / "classify_report.json", report)
    write_summary_md(args.output / "pool_summary.md", rows, args.a_size, args.b_size)
    print(f"pools: {counts}")
    print(f"wrote {args.output / 'classify_report.json'}")
    print(f"wrote {args.output / 'pool_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
