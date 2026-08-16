"""验证优化链路：评分/低信噪比 → 技能图谱 → 优化稿 → DOCX 导出。"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 脚本独立运行时先注入测试用环境，避免强依赖本机 .env
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "verify-optimization-secret")
os.environ.setdefault("ALLOW_REGISTER", "true")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings

get_settings.cache_clear()

from docx import Document

from app.services.analysis_pipeline import run_analysis_pipeline
from app.services.report import generate_rewrite_report


SAMPLE_TEXT = """张三
电话：13800000000 邮箱：zhangsan@example.com
求职意向：数据分析师

教育背景
某某大学 数据科学与大数据技术 本科 2022-2026

实习经历
2025.06-2025.08 某互联网公司 数据分析实习生
参与了很多业务数据分析项目，比较熟悉相关报表工作
协助完成数据清洗与可视化

项目经历
校园二手交易数据分析
使用 Python 完成数据清洗，输出分析结论

技能证书
Python、Excel、沟通能力
"""


def _write_sample_docx(path: Path) -> None:
    doc = Document()
    for line in SAMPLE_TEXT.splitlines():
        doc.add_paragraph(line)
    doc.save(path)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        resume_path = Path(tmp) / "sample_resume.docx"
        _write_sample_docx(resume_path)
        pipeline = run_analysis_pipeline(
            resume_path,
            target_position="数据分析师",
            job_description="要求 Python、SQL、数据可视化与指标分析能力",
            enable_ai=False,
        )
        result = pipeline["result"]
        rewrite = result.get("rewrite_preview") or {}
        optimized = rewrite.get("optimized_resume") or {}
        skill_graph = result.get("skill_graph") or {}
        low_snr = result.get("low_snr_zones") or []

        checks = {
            "total_score": isinstance(result.get("total_score"), (int, float)),
            "has_scores": bool(result.get("scores")),
            "has_optimized": bool(optimized.get("sections") or optimized.get("document_text")),
            "has_diffs": bool(optimized.get("diffs")),
            "has_skill_hints": bool(skill_graph.get("hints")),
            "has_low_snr_or_confidence": bool(low_snr) or result.get("evidence_confidence") is not None,
            "rewrite_mode": rewrite.get("mode") == "offline_star",
        }

        out_path = generate_rewrite_report(999001, "sample_resume.docx", rewrite)
        checks["docx_exists"] = out_path.exists() and out_path.stat().st_size > 500

        print("=== 优化链路验证 ===")
        print(f"总分: {result.get('total_score')}")
        print(f"证据置信度: {result.get('evidence_confidence')}")
        print(f"低信噪比区: {len(low_snr)}")
        print(f"技能提示: {len(skill_graph.get('hints') or [])}")
        print(f"优化稿改动: {optimized.get('change_count')}")
        print(f"DOCX: {out_path} ({out_path.stat().st_size if out_path.exists() else 0} bytes)")
        for key, ok in checks.items():
            print(f"[{'OK' if ok else 'FAIL'}] {key}")

        failed = [key for key, ok in checks.items() if not ok]
        if failed:
            print("FAILED:", ", ".join(failed))
            return 1
        print("ALL CHECKS PASSED")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
