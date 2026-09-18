"""B 池 Bad Case / 能力边界卡生成器。

默认对 data/resume_pools/pool_B 做**本地离线分析**（不依赖异步 API、不调用大模型）：
  - parse_quality / parse_warnings / missing_sections / total_score
  - 输出 Markdown + CSV 边界表（PPT 可直接贴）
  - 可选：--screenshot 用 Playwright 打开前端详情页截图（需服务已启动）

用法:
  cd backend
  .\\.venv\\Scripts\\python.exe scripts\\capture_bad_cases.py
  .\\.venv\\Scripts\\python.exe scripts\\capture_bad_cases.py --pool-dir ..\\data\\resume_pools\\pool_B
  .\\.venv\\Scripts\\python.exe scripts\\capture_bad_cases.py --screenshot --base-url http://127.0.0.1:5174

硬约束:
  - enable_ai=False，禁止用 LLM 给匹配打标
  - 不把结果写进训练集
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "badcase-resume-secret")
os.environ.setdefault("USE_SEMANTIC_MATCH", "false")  # 边界卡聚焦解析质量，避免语义拖慢批处理

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _resume_corpus_common import (  # noqa: E402
    default_pools_dir,
    ensure_dir,
    extract_text,
    iter_resume_files,
    safe_stem,
    write_json,
)

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.services.document_ingest import ingest_resume  # noqa: E402
from app.services.parser import detect_sections, evaluate_parse_quality  # noqa: E402
from app.services.pipeline_utils import CORE_SECTION_KEYS, normalize_sections  # noqa: E402
from app.services.scoring import analyze_resume  # noqa: E402


def layout_feature(text: str, warnings: list[str]) -> str:
    tags: list[str] = []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if any("扫描" in w or "OCR" in w or "图片" in w for w in warnings):
        tags.append("疑似扫描/图片")
    table_like = sum(1 for ln in lines if " | " in ln or "｜" in ln or "\t" in ln)
    if table_like >= 4:
        tags.append("表格痕迹多")
    short = sum(1 for ln in lines if len(ln.strip()) <= 4)
    if lines and short / max(len(lines), 1) >= 0.3:
        tags.append("碎片行多")
    sticky = sum(1 for ln in lines if len(ln) > 120)
    if sticky >= 2:
        tags.append("长行粘连")
    if len(text.strip()) < 120:
        tags.append("正文过短")
    if not tags:
        tags.append("结构不规则")
    return "+".join(tags[:4])


def layout_complexity(text: str) -> float:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0.0
    short_ratio = sum(1 for ln in lines if len(ln) <= 4) / max(len(lines), 1)
    table_lines = sum(1 for ln in lines if " | " in ln or "｜" in ln or "\t" in ln)
    sticky_lines = sum(1 for ln in lines if len(ln) > 120)
    score = 0.0
    if len(lines) >= 40:
        score += 1.2
    elif len(lines) >= 25:
        score += 0.7
    if short_ratio >= 0.35:
        score += 1.3
    elif short_ratio >= 0.2:
        score += 0.6
    if table_lines >= 6:
        score += 1.4
    elif table_lines >= 2:
        score += 0.7
    if sticky_lines >= 2:
        score += 0.6
    return round(score, 3)


def system_behavior(parse_quality: str, warnings: list[str], total: float | None) -> str:
    bits: list[str] = []
    if parse_quality == "low":
        bits.append("解析质量 low：评分封顶降权，跳过 AI 增强")
    elif parse_quality == "medium":
        bits.append("解析质量 medium：结果供参考，保留告警")
    else:
        bits.append("解析质量 high：正常评分")
    if any("OCR" in w or "扫描" in w for w in warnings):
        bits.append("提示优先改用文字版 DOCX/PDF")
    if total is not None and parse_quality == "low" and total <= 58.5:
        bits.append("总分已按低解析策略封顶")
    return "；".join(bits)


def analyze_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    warnings: list[str] = []
    total = None
    scores: dict[str, Any] = {}
    parse_quality = "medium"
    missing: list[str] = []
    sections: dict[str, list[str]] = {}

    if suffix in {".docx", ".pdf"}:
        try:
            parsed = ingest_resume(path)
            result = analyze_resume(parsed, target_position="", job_description="")
            parse_quality = str(result.get("parse_quality") or parsed.get("parse_quality") or "medium")
            warnings = list(result.get("parse_warnings") or parsed.get("parse_warnings") or [])
            missing = list(result.get("evidence", {}).get("missing_sections") or parsed.get("missing_sections") or [])
            sections = normalize_sections(parsed.get("sections") or {})
            total = result.get("total_score")
            scores = result.get("scores") or {}
            text = str(parsed.get("raw_text") or "")
        except Exception as exc:  # noqa: BLE001
            text, warnings = extract_text(path)
            warnings = [*warnings, f"ingest失败回退文本: {exc}"]
            sections = normalize_sections(detect_sections(text))
            parse_quality, pw = evaluate_parse_quality(text, sections, warnings, suffix)
            warnings = list(dict.fromkeys([*warnings, *pw]))
            missing = [k for k in CORE_SECTION_KEYS if not sections.get(k)]
    else:
        text, warnings = extract_text(path)
        sections = normalize_sections(detect_sections(text))
        parse_quality, pw = evaluate_parse_quality(text, sections, warnings, ".txt")
        warnings = list(dict.fromkeys([*warnings, *pw]))
        missing = [k for k in CORE_SECTION_KEYS if not sections.get(k)]
        # 对纯文本也跑一遍评分，便于看是否虚高
        try:
            parsed = {
                "raw_text": text,
                "sections": sections,
                "detected_keywords": [],
                "detected_target_position": "",
                "parse_quality": parse_quality,
                "parse_warnings": warnings,
            }
            result = analyze_resume(parsed, "", "")
            total = result.get("total_score")
            scores = result.get("scores") or {}
            missing = list(result.get("evidence", {}).get("missing_sections") or missing)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"score失败: {exc}")

    core_warn = _pick_core_warning(warnings, missing, parse_quality)
    complexity = layout_complexity(text)
    if complexity >= 3.5 and parse_quality != "low":
        behavior = "版式复杂但正文可用：保留正常评分，标记人工复核"
    else:
        behavior = system_behavior(parse_quality, warnings, float(total) if total is not None else None)
    return {
        "id": safe_stem(path),
        "file": path.name,
        "path": str(path),
        "layout_feature": layout_feature(text, warnings),
        "layout_complexity": complexity,
        "parse_quality": parse_quality,
        "core_warning": core_warn,
        "all_warnings": warnings[:8],
        "missing_sections": missing,
        "section_keys": sorted(k for k, v in sections.items() if v),
        "total_score": total,
        "job_match": (scores.get("job_match") if isinstance(scores, dict) else None),
        "system_behavior": behavior,
        "chars": len(text),
    }


def _pick_core_warning(warnings: list[str], missing: list[str], quality: str) -> str:
    if warnings:
        # 优先带「模块/OCR/噪声/短」的告警
        for key in ("模块", "OCR", "扫描", "噪声", "短", "核心"):
            for w in warnings:
                if key in w:
                    return w[:80]
        return warnings[0][:80]
    if missing:
        labels = {
            "basic_info": "基本信息",
            "education": "教育背景",
            "internship": "实习/工作经历",
            "projects": "项目经历",
            "skills": "技能",
        }
        pretty = "、".join(labels.get(m, m) for m in missing[:3])
        return f"缺失板块: {pretty}"
    if quality == "low":
        return "解析质量偏低"
    return "无明显告警（仍属复杂版式样本）"


def write_table_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# 系统能力边界卡（B 池 Bad Case，脚本自动生成）",
        "",
        "> 用途：答辩展示「复杂版式会告警、低解析会降权，而不是虚高打分」。",
        "",
        "| 简历ID | 版式特征 | 复杂度 | 解析质量 | 核心告警 | 总分 | 系统行为 |",
        "|---|---|---:|---|---|---:|---|",
    ]
    for r in rows:
        total = r.get("total_score")
        total_s = f"{total:.1f}" if isinstance(total, int | float) else "-"
        warn = str(r.get("core_warning") or "").replace("|", "/")
        behavior = str(r.get("system_behavior") or "").replace("|", "/")
        lines.append(
            f"| {r['id']} | {r['layout_feature']} | {r['layout_complexity']:.1f} | "
            f"{str(r['parse_quality']).upper()} | {warn} | {total_s} | {behavior} |"
        )
    lines.extend(
        [
            "",
            "## 答辩话术（可直接念）",
            "",
            "这是我们脚本自动生成的系统能力边界卡。我们承认复杂版式仍是短板，",
            "所以系统会明确告警、在低解析质量时降权封顶，而不是硬给一个虚高分骗用户。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_table_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "file",
        "layout_feature",
        "layout_complexity",
        "parse_quality",
        "core_warning",
        "total_score",
        "missing_sections",
        "system_behavior",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            row = dict(r)
            row["missing_sections"] = ",".join(r.get("missing_sections") or [])
            writer.writerow(row)


def maybe_screenshots(rows: list[dict[str, Any]], out_dir: Path, base_url: str) -> list[str]:
    """可选：需要本机已启动前端，且安装 playwright。

    说明：异步分析页截图依赖登录/上传流程，竞赛环境差异大。
    此处采用「静态边界卡已足够答辩」策略；截图失败不阻断主流程。
    """
    notes: list[str] = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        notes.append("未安装 playwright，已跳过截图。可: pip install playwright && playwright install chromium")
        return notes

    shot_dir = ensure_dir(out_dir / "screenshots")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
            page.screenshot(path=str(shot_dir / "00_home.png"), full_page=True)
            notes.append(f"已截首页: {shot_dir / '00_home.png'}")
            # 详情页因需先上传拿 record_id，这里仅保留首页+说明
            (shot_dir / "README.txt").write_text(
                "批量自动打开每份详情页需要先走上传拿 history id。\n"
                "答辩建议：对 B 池人工上传 2～3 份截「诊断/匹配」页，与 boundary_card.md 对照即可。\n",
                encoding="utf-8",
            )
            browser.close()
    except Exception as exc:  # noqa: BLE001
        notes.append(f"截图失败（不影响边界表）: {exc}")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description="B 池能力边界卡")
    parser.add_argument("--pool-dir", type=Path, default=default_pools_dir() / "pool_B")
    parser.add_argument("--output", type=Path, default=default_pools_dir() / "bad_cases")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--screenshot", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:5174")
    args = parser.parse_args()

    print("=== capture_bad_cases ===")
    files = iter_resume_files(args.pool_dir)
    # 优先 txt
    txts = [p for p in files if p.suffix.lower() == ".txt"]
    files = txts or files
    if args.limit > 0:
        files = files[: args.limit]
    print(f"pool: {args.pool_dir} ({len(files)} files)")
    if not files:
        print("B 池为空。请先 anonymize → classify。")
        return 1

    rows = [analyze_file(p) for p in files]
    ensure_dir(args.output)
    write_json(args.output / "bad_cases_report.json", {"cases": len(rows), "rows": rows})
    write_table_md(args.output / "boundary_card.md", rows)
    write_table_csv(args.output / "boundary_card.csv", rows)

    notes: list[str] = []
    if args.screenshot:
        notes.extend(maybe_screenshots(rows, args.output, args.base_url))

    print(f"wrote {args.output / 'boundary_card.md'}")
    print(f"wrote {args.output / 'boundary_card.csv'}")
    for n in notes:
        print(n)
    low_n = sum(1 for r in rows if r["parse_quality"] == "low")
    print(f"summary: {len(rows)} cases, parse_quality=low → {low_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
