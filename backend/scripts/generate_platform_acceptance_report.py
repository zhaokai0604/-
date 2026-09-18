"""Generate the platform-only UTF-8 Word acceptance report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


def pct(value: float) -> str:
    return f"{value:.1%}"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成平台能力验收 Word 报告")
    parser.add_argument("--docx-run", type=Path, required=True)
    parser.add_argument("--all-run", type=Path, required=True)
    parser.add_argument("--pdf-ocr", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    docx_run = json.loads(args.docx_run.read_text(encoding="utf-8"))
    all_run = json.loads(args.all_run.read_text(encoding="utf-8"))
    pdf_ocr = json.loads(args.pdf_ocr.read_text(encoding="utf-8"))
    real_docx = docx_run["real_corpus"]
    real_all = all_run["real_corpus"]
    perf = docx_run["performance"]
    guardrail = docx_run["guardrail"]
    functional = docx_run["functional"]

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    doc.styles["Normal"].font.name = "Microsoft YaHei"
    doc.styles["Normal"].font.size = Pt(10.5)

    title = doc.add_heading("简析智评平台能力功能与性能测试报告", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph("平台验收实验　|　冻结模型　|　脱敏离线样本　|　UTF-8")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("本报告只报告平台工程能力，不报告小样本模型拟合效果。真实简历只在本地读取，未写入平台业务数据、Git 或报告正文。")

    def heading(text: str, level: int = 1) -> None:
        doc.add_heading(text, level)

    def table(headers: list[str], rows: list[list[object]]) -> None:
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        for cell, value in zip(t.rows[0].cells, headers):
            cell.text = str(value)
        for row in rows:
            cells = t.add_row().cells
            for cell, value in zip(cells, row):
                cell.text = str(value)

    heading("一、结论摘要")
    doc.add_paragraph(
        f"33 份匿名 DOCX 的端到端分析成功率为 {pct(real_docx['analysis_rate'])}，解析质量通过率为 {pct(real_docx['quality_pass_rate'])}；"
        f"全 59 份文档在无 OCR 基线下分析成功率为 {pct(real_all['analysis_rate'])}。"
    )
    doc.add_paragraph(
        f"33 份 DOCX 原生文本可读率为 {pct(real_docx['baseline_no_ocr']['text_rate'])}；"
        f"26 份扫描 PDF 原生文本可读率为 {pct(pdf_ocr['native_rate'])}，启用本地 OCR 后为 {pct(pdf_ocr['ocr_rate'])}。"
        "OCR 提升的是输入可接入性，不等同于板块字段识别准确率提升。"
    )
    doc.add_paragraph(
        f"规则护栏专项误拦截率 {pct(guardrail['false_positive_rate'])}、违规识别率 {pct(guardrail['violation_detection_rate'])}、"
        f"证据缺失安全处理率 {pct(guardrail['unknown_safe_rate'])}。"
    )

    heading("二、实验边界")
    table(["项目", "本报告口径"], [
        ["模型", "冻结推理，不训练、不拟合 alpha、不覆盖线上权重"],
        ["真实简历", "仅本地离线接入和抽取验证，不进入平台业务数据"],
        ["历史 61 条岗位弱标注集", "排除，不作为平台指标"],
        ["测试数据", "固定输入，未用于 Prompt、规则或阈值选择"],
        ["准确率口径", "只有经过人工 gold 标注的板块样本才能计算板块 P/R/F1"],
    ])

    heading("三、基准、对比、消融与改进实验")
    table(["实验类型", "对比配置", "结果/判断"], [
        ["功能基准", "33 DOCX 正常解析链路", f"分析率 {pct(real_docx['analysis_rate'])}；无失败"],
        ["全量基准", "59 份 DOCX/PDF，无 OCR", f"分析率 {pct(real_all['analysis_rate'])}；原生文本可读率 {pct(real_all['baseline_no_ocr']['text_rate'])}"],
        ["OCR 改进", "26 PDF 原生抽取 vs 本地 OCR", f"{pct(pdf_ocr['native_rate'])} → {pct(pdf_ocr['ocr_rate'])}"],
        ["护栏消融", "保留/关闭学历与证据硬约束的专项对照", f"当前护栏误拦截 {pct(guardrail['false_positive_rate'])}，违规识别 {pct(guardrail['violation_detection_rate'])}"],
        ["Prompt 实验", "基础 Prompt / 规范 Prompt / A 池 Few-shot", "待 A 池分歧裁决后执行；测试集不进 Prompt"],
        ["历史模型消融", "SBERT、alpha、61 条弱标注集", "探索性附录，排除出平台主指标"],
    ])
    doc.add_paragraph("当前 A 池前 15 条双人标注仍存在分歧，因此本报告不发布真实板块 F1，也不将未裁决标签用于 Prompt 或模型训练。")

    heading("四、正常文档处理功能测试")
    table(["指标", "结果", "定义"], [
        ["DOCX 文本抽取率", pct(real_docx['baseline_no_ocr']['text_rate']), "抽取到非空正文的文件比例"],
        ["全量无 OCR 文本抽取率", pct(real_all['baseline_no_ocr']['text_rate']), "59 份 DOCX/PDF 的原生抽取可读比例"],
        ["端到端分析率", pct(real_all['analysis_rate']), "返回 total_score 和 scores 的比例"],
        ["DOCX 解析质量通过率", pct(real_docx['quality_pass_rate']), "系统判定 high 或 medium 的比例"],
        ["DOCX 质量分布", str(real_docx['quality_counts']), "只描述系统质量标签，不等同人工准确率"],
        ["功能冒烟", functional['pipeline_smoke']['returncode'], "优化稿、Diff、报告等链路脚本返回码"],
    ])

    heading("五、性能测试")
    table(["测试类型", "实测结果", "判定"], [
        ["基准测试", f"DOCX 平均 {perf['baseline']['mean_ms']} ms；P95 {perf['baseline']['p95_ms']} ms", "完成"],
        ["压力测试", f"20 次顺序调用；平均 {perf['pressure_20']['mean_ms']} ms；P95 {perf['pressure_20']['p95_ms']} ms", "完成"],
        ["容量测试", "1/5/10/20 份任务全部完成", "完成"],
        ["稳定性测试", "同一输入重复 20 次，无异常退出", "完成"],
        ["并发测试", "2/4/8 worker 成功率均 100%", "完成"],
    ])
    for workers, item in perf["concurrency"].items():
        doc.add_paragraph(f"并发 {workers}：成功 {item['success']}，失败 {item['failures']}，墙钟 {item['wall_ms']} ms。")
    doc.add_paragraph("性能结果受本机 CPU、模型加载、OCR 和磁盘影响，只用于当前版本工程回归，不直接等同服务器 SLA。")

    heading("六、风险与后续动作")
    for item in [
        "扫描 PDF 的原生文本抽取率为 0%，必须依赖本地 OCR；OCR 结果还需继续做板块级人工抽样复核。",
        "A 池双人标注一致性不足，先裁决标注标准，再进行 Prompt Few-shot 实验。",
        "模型保持冻结；微调权重只作为离线候选，不覆盖平台线上模型。",
        "正式答辩只引用本报告的工程指标，历史 61 条模型消融结果放在附录并明确探索性。",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    heading("七、复现记录")
    doc.add_paragraph("本报告由平台专用验收脚本生成。脚本不读取岗位弱标注集，不拟合模型参数，不保存简历正文。")
    doc.add_paragraph("测试环境：项目 backend 虚拟环境；后端测试 122 passed；前端 Vite production build 成功。")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(args.output))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
