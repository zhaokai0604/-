from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.scoring import label_for_score


def generate_reports(record_id: int, filename: str, result: dict[str, Any]) -> dict[str, Path]:
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    stem = f"analysis_{record_id}"
    docx_path = settings.reports_dir / f"{stem}.docx"
    pdf_path = settings.reports_dir / f"{stem}.pdf"
    generate_docx_report(docx_path, filename, result)
    generate_pdf_report(pdf_path, filename, result)
    return {"docx": docx_path, "pdf": pdf_path}


def generate_docx_report(path: Path, filename: str, result: dict[str, Any]) -> None:
    from docx import Document

    doc = Document()
    doc.add_heading("简历评价报告", level=0)
    doc.add_paragraph(f"文件名：{filename}")
    doc.add_paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"分析模式：{_analysis_mode_label(result.get('analysis_mode', 'offline'))}")
    if result.get("ai_fallback_reason"):
        doc.add_paragraph(f"回退说明：{result['ai_fallback_reason']}")
    _add_parse_quality_docx(doc, result)
    doc.add_heading("总评分", level=1)
    doc.add_paragraph(f"{result.get('total_score', 0)} / 100")
    doc.add_heading("分项评分", level=1)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "维度"
    table.rows[0].cells[1].text = "分数"
    for key, score in result.get("scores", {}).items():
        row = table.add_row().cells
        row[0].text = label_for_score(key)
        row[1].text = str(score)
    _add_list_section(doc, "问题诊断", result.get("diagnosis", []))
    _add_list_section(doc, "修改建议", result.get("suggestions", []))
    match = result.get("match_result", {})
    doc.add_heading("岗位匹配分析", level=1)
    doc.add_paragraph(f"采用岗位：{match.get('target_position') or '未识别，使用通用建议'}")
    doc.add_paragraph(f"岗位来源：{_target_source_label(match.get('target_source', 'generic'))}")
    doc.add_paragraph(match.get("summary", ""))
    if match.get("missing_keywords"):
        doc.add_paragraph("建议补充关键词：" + "、".join(match["missing_keywords"]))
    doc.save(path)


def _add_parse_quality_docx(doc: Any, result: dict[str, Any]) -> None:
    quality = result.get("parse_quality")
    if not quality:
        return
    doc.add_heading("解析质量", level=1)
    doc.add_paragraph(_parse_quality_label(quality))
    warnings = result.get("parse_warnings") or []
    for item in warnings:
        doc.add_paragraph(item, style="List Bullet")


def _add_list_section(doc: Any, title: str, items: list[str]) -> None:
    doc.add_heading(title, level=1)
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def generate_pdf_report(path: Path, filename: str, result: dict[str, Any]) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font_name = _register_chinese_font()
    styles = _build_pdf_styles(font_name)
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    story: list[Any] = []
    story.append(Paragraph("简历评价报告", styles["Title"]))
    story.append(Paragraph(f"文件名：{filename}", styles["Normal"]))
    story.append(Paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Paragraph(f"分析模式：{_analysis_mode_label(result.get('analysis_mode', 'offline'))}", styles["Normal"]))
    if result.get("ai_fallback_reason"):
        story.append(Paragraph(f"回退说明：{result['ai_fallback_reason']}", styles["Normal"]))
    _add_parse_quality_pdf(story, styles, result)
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"总评分：{result.get('total_score', 0)} / 100", styles["Heading2"]))
    rows = [["维度", "分数"]] + [[label_for_score(key), str(score)] for key, score in result.get("scores", {}).items()]
    table = Table(rows, colWidths=[95 * mm, 40 * mm])
    table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font_name), ("GRID", (0, 0), (-1, -1), 0.5, "#B8C1CC"), ("BACKGROUND", (0, 0), (-1, 0), "#E8F0F7")]))
    story.append(table)
    _pdf_section(story, styles, "问题诊断", result.get("diagnosis", []))
    _pdf_section(story, styles, "修改建议", result.get("suggestions", []))
    match = result.get("match_result", {})
    story.append(Paragraph("岗位匹配分析", styles["Heading2"]))
    story.append(Paragraph(f"采用岗位：{match.get('target_position') or '未识别，使用通用建议'}", styles["Normal"]))
    story.append(Paragraph(f"岗位来源：{_target_source_label(match.get('target_source', 'generic'))}", styles["Normal"]))
    story.append(Paragraph(match.get("summary", ""), styles["Normal"]))
    if match.get("missing_keywords"):
        story.append(Paragraph("建议补充关键词：" + "、".join(match["missing_keywords"]), styles["Normal"]))
    doc.build(story)


def _build_pdf_styles(font_name: str) -> Any:
    from reportlab.lib.styles import getSampleStyleSheet

    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name
        if hasattr(style, "leading") and hasattr(style, "fontSize"):
            style.leading = max(style.leading, style.fontSize + 4)
    return styles


def _add_parse_quality_pdf(story: list[Any], styles: Any, result: dict[str, Any]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    quality = result.get("parse_quality")
    if not quality:
        return
    story.append(Spacer(1, 8))
    story.append(Paragraph("解析质量", styles["Heading2"]))
    story.append(Paragraph(_parse_quality_label(quality), styles["Normal"]))
    for item in result.get("parse_warnings") or []:
        story.append(Paragraph("- " + item, styles["Normal"]))


def _pdf_section(story: list[Any], styles: Any, title: str, items: list[str]) -> None:
    from reportlab.platypus import Paragraph, Spacer

    story.append(Spacer(1, 8))
    story.append(Paragraph(title, styles["Heading2"]))
    for item in items:
        story.append(Paragraph("- " + item, styles["Normal"]))


def _register_chinese_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = list(settings.fonts_dir.glob("*.ttf")) + list(settings.fonts_dir.glob("*.otf"))
    windows_fonts = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ]
    linux_fonts = [
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
    ]
    candidates.extend(path for path in windows_fonts if path.exists())
    candidates.extend(path for path in linux_fonts if path.exists())
    for candidate in candidates:
        try:
            pdfmetrics.registerFont(TTFont("ResumeChinese", str(candidate)))
            return "ResumeChinese"
        except Exception:
            continue
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception:
        pass
    return "Helvetica"


def _analysis_mode_label(mode: str) -> str:
    labels = {
        "deepseek": "DeepSeek 已使用",
        "offline_fallback": "DeepSeek 不可用，已回退离线规则分析",
        "offline": "离线规则分析",
    }
    return labels.get(mode, mode)


def _target_source_label(source: str) -> str:
    labels = {
        "manual": "手动输入岗位",
        "detected": "简历识别岗位",
        "generic": "通用建议",
    }
    return labels.get(source, source)


def _parse_quality_label(quality: str) -> str:
    labels = {
        "high": "高：正文和核心模块识别较完整。",
        "medium": "中：已完成分析，但建议核对部分模块识别结果。",
        "low": "低：正文提取不足，评分仅供参考。",
    }
    return labels.get(quality, quality)
