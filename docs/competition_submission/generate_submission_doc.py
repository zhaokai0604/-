from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import math
import re
import sys
from collections import Counter

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from figure_builder import ensure_figure_assets

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "docs" / "competition_submission" / "output"
ASSET_DIR = OUTPUT_DIR / "assets"
DOCX_PATH = OUTPUT_DIR / "简历评价与分析平台参赛文档（20260630）.docx"
FONT_PATH = ROOT / "assets" / "fonts" / "NotoSansSC-Regular.ttf"


TITLE = "简历评价与分析平台"
SUBTITLE = "面向高校求职场景的简历解析、评价、岗位匹配与报告输出平台"
VERSION = "V2.0 参赛文档"
FINISH_DATE = "2026年8月3日"


THEME_BLUE = RGBColor(34, 91, 170)
THEME_DARK = RGBColor(20, 45, 90)
THEME_LIGHT = RGBColor(232, 239, 250)
THEME_LIGHTER = RGBColor(244, 247, 252)
TEXT_GRAY = RGBColor(80, 80, 80)
FIGURE_PATHS: dict[str, Path] = {}


TEST_TOPIC_LABELS = {
    "test_analysis_flow.py": "主流程串联验证",
    "test_analysis_pipeline.py": "分析流水线与结果组织",
    "test_async_analysis.py": "异步分析与任务编排",
    "test_batch_service.py": "ZIP 批量处理",
    "test_database_schema.py": "数据库结构与字段约束",
    "test_interview_engine.py": "面试准备与问答生成",
    "test_match_engine.py": "岗位匹配与证据提取",
    "test_parser.py": "文档解析与结构化识别",
    "test_phase2_features.py": "平台化功能补充验证",
    "test_platform.py": "平台 API 与工作台主流程",
    "test_resume_templates.py": "模板推荐能力",
    "test_score_policy.py": "评分策略配置",
    "test_scoring.py": "评分引擎与维度结果",
    "test_teacher_classes.py": "教师班级统计",
    "test_teacher_records.py": "教师记录查看边界",
    "test_weight_templates.py": "岗位权重模板",
    "test_zip_service.py": "ZIP 安全校验与过滤",
}


ROUTE_MODULE_LABELS = {
    "analysis_routes.py": "分析主链",
    "auth_routes.py": "认证与会话",
    "job_routes.py": "岗位画像",
    "teacher_routes.py": "教师端",
    "users_routes.py": "个人资料",
    "workspace_routes.py": "任务与报告中心",
    "admin_routes.py": "管理端",
}


SERVICE_MODULE_LABELS = {
    "ai.py": "AI 增强诊断与回退控制",
    "ai_http.py": "外部 AI HTTP 调用封装",
    "analysis_pipeline.py": "分析主流程编排",
    "auth.py": "认证与密码逻辑",
    "batch_service.py": "批量任务处理",
    "config_cache.py": "运行时配置缓存",
    "document_ingest.py": "统一文档接入",
    "file_lifecycle.py": "上传与报告文件生命周期管理",
    "interview_engine.py": "面试准备与模拟面试生成",
    "job_profile_presets.py": "岗位预置模板",
    "match_engine.py": "岗位关键词匹配与证据提取",
    "parser.py": "简历解析与结构化识别",
    "pipeline_utils.py": "流水线公共工具与字段规范",
    "rate_limit.py": "限流与保护控制",
    "report.py": "Word/PDF 报告生成",
    "resume_rewriter.py": "改写预览与优化稿生成",
    "resume_template_engine.py": "简历模板推荐",
    "runtime_config.py": "运行期配置读取",
    "score_engine.py": "六维评分与证据构建",
    "scoring.py": "评分主入口与结果封装",
    "stats_service.py": "统计数据聚合",
    "storage.py": "存储路径与文件操作",
    "suggestion_engine.py": "诊断建议与行动路线图",
    "teacher_class_stats.py": "教师班级统计",
    "teacher_review_service.py": "教师记录视图与汇总",
    "zip_service.py": "ZIP 安全校验与解压",
}


@dataclass
class FigureItem:
    code: str
    title: str
    summary: str


@dataclass
class TableItem:
    code: str
    title: str
    headers: list[str]
    rows: list[list[str]]


def set_run_font(run, size: float | None = None, bold: bool | None = None, color: RGBColor | None = None, name: str = "Arial") -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:ascii"), name)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), name)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_begin)
    run._r.append(instr_text)
    run._r.append(fld_char_end)
    set_run_font(run, 9, color=TEXT_GRAY)


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)

    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    style.font.size = Pt(11)
    pf = style.paragraph_format
    pf.space_after = Pt(6)
    pf.line_spacing = 1.15

    for name, size, color in [
        ("Heading 1", 16, THEME_BLUE),
        ("Heading 2", 13, THEME_BLUE),
        ("Heading 3", 12, THEME_DARK),
    ]:
        st = doc.styles[name]
        st.font.name = "Arial"
        st._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = color
        st.paragraph_format.space_before = Pt(12 if name != "Heading 3" else 8)
        st.paragraph_format.space_after = Pt(6 if name != "Heading 3" else 4)
        st.paragraph_format.line_spacing = 1.15

    footer = section.footer
    p = footer.paragraphs[0]
    add_page_number(p)


def add_cover(doc: Document) -> None:
    for _ in range(3):
        doc.add_paragraph("")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(TITLE)
    set_run_font(r, 24, True, THEME_DARK)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("参赛文档")
    set_run_font(r, 18, True, THEME_BLUE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(SUBTITLE)
    set_run_font(r, 12, False, TEXT_GRAY)
    for _ in range(6):
        doc.add_paragraph("")

    info_rows = [
        ["项目名称", TITLE],
        ["项目定位", "高校就业指导数字化场景下的简历评价与岗位匹配平台"],
        ["文档版本", VERSION],
        ["完成日期", FINISH_DATE],
        ["编制依据", "项目源码、最新政策信息、赛题要求、测试结果、部署与安全说明"],
        ["适用用途", "比赛提交、项目答辩、成果展示与归档留存"],
    ]
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    set_table_widths(table, [Cm(4.0), Cm(11.8)])
    for idx, row in enumerate(info_rows):
        cells = table.rows[0].cells if idx == 0 else table.add_row().cells
        cells[0].text = row[0]
        cells[1].text = row[1]
    style_table(table, header=False)
    doc.add_page_break()


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_table_widths(table, widths) -> None:
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = width


def style_table(table, header: bool = True, font_size: float = 10.5) -> None:
    for i, row in enumerate(table.rows):
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.line_spacing = 1.08
                for run in p.runs:
                    set_run_font(run, font_size)
            if i == 0 and header:
                set_cell_shading(cell, "E8EFFA")
                for p in cell.paragraphs:
                    for run in p.runs:
                        set_run_font(run, font_size, True, THEME_DARK)


def add_section_heading(doc: Document, level: int, text: str) -> None:
    doc.add_heading(text, level=level)


def add_body_paragraph(doc: Document, text: str, first_line: bool = False) -> None:
    p = doc.add_paragraph()
    if first_line:
        p.paragraph_format.first_line_indent = Cm(0.74)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    set_run_font(r, 11)


def add_figure_note(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    r1 = p.add_run("图示说明：")
    set_run_font(r1, 10.6, True, THEME_DARK)
    r2 = p.add_run(text)
    set_run_font(r2, 10.6, False, TEXT_GRAY)


def add_bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.1
    r = p.add_run(text)
    set_run_font(r, 10.8)


def add_number(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.1
    r = p.add_run(text)
    set_run_font(r, 10.8)


def add_caption(doc: Document, prefix: str, title: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(f"{prefix} {title}")
    set_run_font(r, 9.5, False, TEXT_GRAY)


def add_figure_placeholder(doc: Document, item: FigureItem) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.cell(0, 0)
    cell.width = Cm(15.8)
    set_cell_shading(cell, "F4F7FC")
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(26)
    p.paragraph_format.space_after = Pt(16)
    r = p.add_run("示意图生成失败")
    set_run_font(r, 16, True, THEME_BLUE)
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(item.summary)
    set_run_font(r, 10.5, False, TEXT_GRAY)
    cell.add_paragraph("")
    add_caption(doc, item.code, item.title)


def add_figure_image(doc: Document, item: FigureItem, image_path: Path, width_cm: float = 15.8) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(image_path), width=Cm(width_cm))
    p.paragraph_format.space_after = Pt(4)
    add_caption(doc, item.code, item.title)


def add_table_block(doc: Document, item: TableItem, widths_cm: list[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(item.headers))
    table.style = "Table Grid"
    headers = table.rows[0].cells
    for cell, text in zip(headers, item.headers):
        cell.text = text
    for row in item.rows:
        cells = table.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = text
    if widths_cm:
        set_table_widths(table, [Cm(w) for w in widths_cm])
    style_table(table)
    add_caption(doc, item.code, item.title)


def _figure(doc: Document, item: FigureItem) -> None:
    image_path = FIGURE_PATHS.get(item.code)
    if image_path and image_path.exists():
        add_figure_image(doc, item, image_path)
    else:
        raise FileNotFoundError(f"缺少参赛文档图示资源: {item.code}")


def get_test_file_breakdown() -> list[list[str]]:
    test_dir = ROOT / "backend" / "tests"
    rows: list[list[str]] = []
    for path in sorted(test_dir.glob("test_*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        count = text.count("def test_")
        rows.append([path.name, TEST_TOPIC_LABELS.get(path.name, "功能验证"), str(count)])
    return rows


def get_test_category_breakdown() -> list[list[str]]:
    rows = get_test_file_breakdown()
    categories = Counter()
    mapping = {
        "解析与识别": {"test_parser.py", "test_zip_service.py"},
        "分析主链与评分": {"test_analysis_flow.py", "test_analysis_pipeline.py", "test_scoring.py", "test_score_policy.py", "test_weight_templates.py", "test_match_engine.py"},
        "平台接口与异步任务": {"test_async_analysis.py", "test_platform.py", "test_batch_service.py"},
        "教师端与治理": {"test_teacher_classes.py", "test_teacher_records.py", "test_database_schema.py"},
        "增强功能": {"test_interview_engine.py", "test_resume_templates.py", "test_phase2_features.py"},
    }
    reverse: dict[str, str] = {}
    for category, files in mapping.items():
        for file in files:
            reverse[file] = category
    for name, _, count in rows:
        categories[reverse.get(name, "其他")] += int(count)
    return [[k, str(v)] for k, v in categories.items()]


def get_route_overview_rows() -> list[list[str]]:
    api_dir = ROOT / "backend" / "app" / "api"
    rows: list[list[str]] = []
    for path in sorted(api_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        matches = re.findall(r'@router\.(get|post|put|delete|patch)\("([^"]+)"', text)
        rows.append([path.name, ROUTE_MODULE_LABELS.get(path.name, "业务接口"), str(len(matches))])
    return rows


def get_key_endpoint_rows() -> list[list[str]]:
    api_dir = ROOT / "backend" / "app" / "api"
    rows: list[list[str]] = []
    focus = [
        ("analysis_routes.py", {"POST /resumes/analyze", "POST /resumes/analyze-zip", "GET /history/{record_id}/report/download", "GET /history/{record_id}"}),
        ("teacher_routes.py", {"GET /teacher/stats", "GET /teacher/classes", "GET /teacher/records", "GET /teacher/stats/export"}),
        ("admin_routes.py", {"GET /admin/stats", "GET /admin/users", "GET /admin/audit-logs", "POST /admin/storage/cleanup"}),
        ("workspace_routes.py", {"GET /tasks", "GET /reports", "GET /reports/{report_id}/download"}),
    ]
    for filename, wanted in focus:
        path = api_dir / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        matches = re.findall(r'@router\.(get|post|put|delete|patch)\("([^"]+)"', text)
        for method, route in matches:
            label = f"{method.upper()} {route}"
            if label in wanted:
                rows.append([label, ROUTE_MODULE_LABELS.get(filename, filename), _endpoint_purpose(label)])
    return rows


def get_all_endpoint_rows() -> list[list[str]]:
    api_dir = ROOT / "backend" / "app" / "api"
    rows: list[list[str]] = []
    for path in sorted(api_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        matches = re.findall(r'@router\.(get|post|put|delete|patch)\("([^"]+)"', text)
        for method, route in matches:
            label = f"{method.upper()} {route}"
            rows.append([label, ROUTE_MODULE_LABELS.get(path.name, path.name), _full_endpoint_purpose(label)])
    return rows


def get_all_endpoint_rows_split() -> tuple[list[list[str]], list[list[str]]]:
    rows = get_all_endpoint_rows()
    midpoint = math.ceil(len(rows) / 2)
    return rows[:midpoint], rows[midpoint:]


def get_service_module_rows() -> list[list[str]]:
    service_dir = ROOT / "backend" / "app" / "services"
    rows: list[list[str]] = []
    for path in sorted(service_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        rows.append([path.name, SERVICE_MODULE_LABELS.get(path.name, "业务服务模块")])
    return rows


def get_service_module_rows_split() -> tuple[list[list[str]], list[list[str]]]:
    rows = get_service_module_rows()
    midpoint = math.ceil(len(rows) / 2)
    return rows[:midpoint], rows[midpoint:]


def _endpoint_purpose(label: str) -> str:
    purposes = {
        "POST /resumes/analyze": "单份简历主流程分析入口",
        "POST /resumes/analyze-zip": "ZIP 批量任务入口",
        "GET /history/{record_id}/report/download": "下载单份分析报告",
        "GET /history/{record_id}": "查看分析详情与结构化结果",
        "GET /teacher/stats": "教师端统计总览",
        "GET /teacher/classes": "班级维度分析",
        "GET /teacher/records": "教师端记录元数据列表",
        "GET /teacher/stats/export": "统计结果导出",
        "GET /admin/stats": "管理端运行概览",
        "GET /admin/users": "用户管理",
        "GET /admin/audit-logs": "审计日志查看",
        "POST /admin/storage/cleanup": "运行期文件清理",
        "GET /tasks": "任务中心",
        "GET /reports": "报告中心",
        "GET /reports/{report_id}/download": "下载报告中心产物",
    }
    return purposes.get(label, "平台功能接口")


def _full_endpoint_purpose(label: str) -> str:
    detailed = {
        "GET /resume-templates/catalog": "查看简历模板目录",
        "GET /health": "系统健康检查",
        "POST /resumes/analyze": "单份简历分析",
        "POST /resumes/analyze-zip": "ZIP 批量分析",
        "POST /batch-tasks/{batch_task_id}/pause": "暂停批量任务",
        "POST /batch-tasks/{batch_task_id}/retry": "重试批量任务",
        "GET /history": "查看历史分析记录列表",
        "POST /history/bulk-delete": "批量删除历史记录",
        "GET /history/compare": "历史结果对比",
        "POST /history/{record_id}/retry": "重新分析指定记录",
        "POST /history/{record_id}/rewrite-preview/refresh": "刷新改写预览",
        "POST /history/{record_id}/interview-prep/refresh": "刷新面试准备内容",
        "GET /history/{record_id}/rewrite-report": "下载改写结果报告",
        "GET /batch-tasks/{batch_task_id}": "查看批量任务详情",
        "GET /history/{record_id}/report/download": "下载单份分析报告",
        "GET /history/{record_id}/status": "查看记录处理状态",
        "GET /history/{record_id}": "查看分析详情",
        "GET /history/{record_id}/versions": "查看版本记录",
        "GET /resumes/{record_id}/source": "查看原始简历内容",
        "POST /auth/register": "用户注册",
        "POST /auth/login": "用户登录",
        "POST /auth/logout": "用户退出登录",
        "GET /auth/me": "查看当前会话信息",
        "POST /auth/import-guest-history": "导入游客历史记录",
        "GET /job-profiles": "查看岗位画像列表",
        "GET /job-profile-presets": "查看岗位预置模板",
        "POST /job-profile-presets/{preset_id}/copy": "复制岗位预置模板",
        "POST /job-profiles": "新建岗位画像",
        "PUT /job-profiles/{job_profile_id}": "更新岗位画像",
        "DELETE /job-profiles/{job_profile_id}": "删除岗位画像",
        "GET /teacher/stats": "教师端统计总览",
        "GET /teacher/classes": "教师端班级统计",
        "GET /teacher/records": "教师端记录列表",
        "GET /teacher/stats/export": "导出教师统计数据",
        "GET /users/me/profile": "查看个人资料",
        "PATCH /users/me/profile": "更新个人资料",
        "GET /tasks": "查看任务中心列表",
        "GET /reports": "查看报告中心列表",
        "GET /reports/{report_id}/download": "下载报告中心产物",
        "DELETE /history/{record_id}": "删除单条历史记录",
        "GET /admin/jobs": "查看管理端岗位模板与画像",
        "GET /admin/stats": "查看管理端运行统计",
        "GET /admin/users": "查看用户列表",
        "PATCH /admin/users/{user_id}/status": "修改用户启用状态",
        "PATCH /admin/users/{user_id}/role": "修改用户角色",
        "POST /admin/users/{user_id}/reset-password": "重置用户密码",
        "GET /admin/records": "查看记录元数据",
        "DELETE /admin/records/{record_id}": "删除指定记录",
        "GET /admin/audit-logs": "查看审计日志",
        "GET /admin/ai-config": "查看 AI 配置",
        "PUT /admin/ai-config": "更新 AI 配置",
        "GET /admin/score-config": "查看评分配置",
        "PUT /admin/score-config": "更新评分配置",
        "POST /admin/storage/cleanup": "执行存储清理",
    }
    return detailed.get(label, _endpoint_purpose(label))


def add_quote_box(doc: Document, title: str, body: str) -> None:
    table = doc.add_table(rows=2, cols=1)
    table.style = "Table Grid"
    set_cell_shading(table.cell(0, 0), "E8EFFA")
    p = table.cell(0, 0).paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(title)
    set_run_font(r, 11, True, THEME_DARK)
    p = table.cell(1, 0).paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(body)
    set_run_font(r, 10.5)
    style_table(table, header=False, font_size=10.5)


def add_toc_placeholder(doc: Document) -> None:
    add_section_heading(doc, 1, "目录")
    add_body_paragraph(doc, "本参赛稿采用“前置概览—正文论证—附录证明”的结构组织。目录不仅用于导航，也服务于评委快速判断作品是否具备完整项目书形态，因此保留图目录与表目录，并在附录中进一步列出测试、接口与治理证明材料。")
    toc_lines = [
        "摘  要",
        "参赛亮点总览",
        "图目录",
        "表目录",
        "1. 项目概述",
        "2. 解决方案",
        "3. 关键技术",
        "4. 应用价值",
        "5. 系统优化与展望",
        "参考文献",
        "附录A 测试验证与支撑材料",
        "附录B 部署运行与接口清单",
        "附录C 数据安全、治理与运行边界说明",
        "附录A-扩 测试明细与分类统计",
        "附录B-扩 API 模块与路由规模概览",
    ]
    for line in toc_lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(f"{line} ................................................")
        set_run_font(r, 11)
    doc.add_page_break()


def build_summary(doc: Document) -> None:
    add_section_heading(doc, 1, "摘  要")
    paragraphs = [
        "高校毕业生求职竞争持续加剧，简历质量、岗位匹配度与反馈效率已经成为影响求职成功率的重要变量。根据2025年11月20日新华网援引教育部信息披露，2026届全国普通高校毕业生规模预计达到1270万人，同比增加48万人。毕业生规模扩张叠加岗位结构分化，使高校就业指导工作面临服务对象数量大、反馈周期短、人工辅导成本高、结果难沉淀等现实压力。",
        "在此背景下，本文围绕现有项目仓库与赛题要求，形成《简历评价与分析平台》参赛文档。平台面向高校就业指导场景，支持DOCX、PDF与ZIP批量输入，能够完成文档接入、安全校验、结构化解析、六维评价、岗位证据匹配、问题诊断、修改建议生成以及Word/PDF报告输出，并通过学生端、教师端、管理端三类角色协同，形成从上传、分析、展示、导出到记录沉淀的完整服务闭环。",
        "在技术路线方面，系统采用前后端分离架构：前端基于Vue 3与Vite构建工作台和图表展示界面，后端基于FastAPI、SQLAlchemy和MySQL构建分析与治理服务，辅以Redis和Celery支持异步任务编排。平台分析主链以文档解析、结构化字段识别、规则评分、岗位匹配和可执行建议为核心，并通过可选DeepSeek增强服务补充诊断表达、改写预览与面试准备能力，同时保留完整的离线规则回退策略，以确保比赛环境中的稳定性、解释性与可复现性。",
        "在结果表达方面，平台不是简单输出单一总分，而是围绕内容完整性、经历相关性、语言专业性、格式规范性、亮点量化程度和岗位语义匹配六个维度生成量化结果，进一步结合岗位关键词覆盖、证据片段、缺失要素和行动路线图输出具有落地性的优化建议。相较于常见只提供模板推荐或笼统建议的同类工具，本项目更强调“哪里有问题、为什么是问题、如何修改、与目标岗位差距在哪里”的闭环表达。",
        "在工程验证方面，截至2026年8月3日，项目后端包含25个测试文件、107个测试函数，本机执行pytest结果为107 passed、122 warnings；前端生产构建通过，Vite完成2161个模块转换并生成dist产物。测试与构建结果表明，该平台具备较强的功能完整性、演示可靠性与工程成熟度。",
        "综合来看，简历评价与分析平台既可以服务学生个体的简历优化和岗位准备，也能够为教师端群体指导与学校端就业服务数字化提供支撑。平台在问题界定、方案组织、关键技术、应用价值和验证材料上形成了较为完整的参赛作品结构，具备较好的展示效果、推广潜力与后续扩展空间。",
    ]
    for text in paragraphs:
        add_body_paragraph(doc, text, first_line=True)
    doc.add_page_break()


def build_key_highlights(doc: Document) -> None:
    add_section_heading(doc, 1, "参赛亮点总览")
    add_body_paragraph(doc, "为帮助评委在前几页内快速把握作品重点，本页从赛题痛点、平台闭环、技术路线、工程验证和应用价值五个方面概括本项目的核心亮点。其作用不是替代后文章节，而是提前建立阅读抓手，使后续方案与技术细节更容易被准确理解。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表H-1",
            "项目核心亮点总览",
            ["亮点方向", "核心结论", "支撑依据"],
            [
                ["赛题痛点抓取准确", "围绕高校就业指导中的简历分析与岗位匹配真实问题展开", "2026届毕业生规模、就业服务体系建设与24365相关公开信息"],
                ["平台闭环完整", "完成上传、解析、评价、匹配、建议、导出、沉淀全流程", "学生端、教师端、管理端与任务中心、报告中心联动"],
                ["技术路线稳健", "规则主链负责稳定性与解释性，AI增强负责表达优化", "analysis_pipeline、score_engine、match_engine、offline_fallback 逻辑"],
                ["工程证明充分", "测试、构建、部署、安全材料齐全，不是空壳调用", "107 passed、前端 build 通过、ci.yml、部署指南、安全说明"],
                ["应用价值清晰", "同时面向学生、教师和学校三层角色形成价值闭环", "应用价值章节与教师统计、管理治理模块实现"],
            ],
        ),
        [3.2, 5.8, 6.8],
    )
    add_quote_box(
        doc,
        "评审关注提示",
        "本项目不是单点打分工具，而是围绕高校就业指导场景构建的简历服务平台。技术章节重点看主链是否真实可运行，附录章节重点看测试、接口、部署与安全边界证明。",
    )
    doc.add_page_break()


def build_figure_list(doc: Document, figures: list[FigureItem]) -> None:
    add_section_heading(doc, 1, "图目录")
    add_body_paragraph(doc, "全文图示既承担说明架构与流程的作用，也承担帮助评委快速建立结构印象的作用。因此图目录保留全部图号，便于答辩时快速定位到关键页面。")
    for item in figures:
        p = doc.add_paragraph()
        r = p.add_run(f"{item.code} {item.title} ................................................")
        set_run_font(r, 10.8)
    doc.add_page_break()


def build_table_list(doc: Document, tables: list[TableItem]) -> None:
    add_section_heading(doc, 1, "表目录")
    add_body_paragraph(doc, "表格是本稿的重要论证载体，用于承接赛题对应关系、功能结构、技术字段、测试结果、接口清单和治理边界等高密度信息。保留完整表目录能够增强正式项目书观感，也便于评审快速跳读。")
    for item in tables:
        p = doc.add_paragraph()
        r = p.add_run(f"{item.code} {item.title} ................................................")
        set_run_font(r, 10.8)
    doc.add_page_break()


def chapter_one(doc: Document) -> None:
    add_section_heading(doc, 1, "1. 项目概述")
    add_section_heading(doc, 2, "1.1 研究背景与研究意义")
    add_section_heading(doc, 3, "1.1.1 高校毕业生规模持续扩大，就业服务数字化需求显著提升")
    for text in [
        "根据2025年11月20日新华网援引教育部披露的信息，2026届全国普通高校毕业生规模预计达到1270万人，同比增加48万人。毕业生规模持续上升意味着高校就业指导工作所面对的服务对象数量和反馈压力同步增加，传统依靠线下讲座、人工简历批改和点对点辅导的方式，已经难以在毕业季高峰场景下提供足够及时、足够细致且可持续沉淀的支持。",
        "2025年4月8日发布的《关于加快构建普通高等学校毕业生高质量就业服务体系的意见》明确提出，要经过3至5年持续努力，基本建立覆盖全员、功能完备、保障有力的高校毕业生就业服务体系，并提出建强国家大学生就业服务平台、打造“24365校园招聘服务”等品牌。这表明高校就业服务正在从单点信息发布转向平台化、数据化和智能化协同。",
        "对于学生而言，简历已经不是简单的信息罗列材料，而是展示学习经历、实践能力、岗位理解和职业准备程度的核心载体。简历表达是否清晰、是否突出成果、是否匹配目标岗位，往往直接影响笔试、面试与筛选机会。对学校而言，如何以更低的人力成本、更高的反馈效率支撑大规模毕业生求职，已成为就业服务数字化建设中的现实问题。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表1-1",
            "赛题关注问题与项目对应切入点",
            ["赛题关注点", "现实问题表现", "本项目切入方式"],
            [
                ["简历识别与读取", "不同格式文档解析效果不稳定", "支持 DOCX、PDF、ZIP，并加入格式校验与安全处理"],
                ["评价与诊断", "仅有总分无法指导修改", "构建六维评价与结构化问题归纳"],
                ["岗位适配", "学生简历与目标岗位匹配不足", "输出岗位证据、缺失关键词与调整方向"],
                ["结果展示", "分析结论难以沉淀与复用", "建设报告中心、历史记录与导出机制"],
                ["平台协同", "教师难以查看群体性问题", "建设教师端、管理端与统计看板"],
            ],
        ),
        [3.1, 5.4, 7.3],
    )
    add_section_heading(doc, 3, "1.1.2 人工指导标准不一、反馈滞后，难以覆盖大规模毕业生群体")
    for text in [
        "传统高校简历指导往往以辅导员、就业指导教师或相关课程教师人工审阅为主。这种方式在服务少量学生时具有针对性，但在大规模毕业生场景中容易暴露出效率瓶颈：不同指导者的关注重点不一、评价口径难统一、修改意见不易沉淀复用，学生常常需要经过多轮重复沟通才能得到可执行的修改方案。",
        "学生端的典型困境表现为“知道简历有问题，但不知道问题具体出在哪里”“知道经历不够突出，但不知道如何面向岗位修改”。如果系统只能给出笼统评价，仍然无法显著降低修改成本；只有当平台能够同时输出结构化问题、对应证据和可执行建议时，才具备真正的辅助价值。",
        "教师和学校端更关注群体层面的洞察与治理能力。单份简历分析结论无法支撑班级、专业、年级层面的指导决策，必须通过任务中心、教师看板、统计图表和历史记录等机制，把分散的个体分析结果沉淀为可回看的服务资产。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_section_heading(doc, 3, "1.1.3 平台化、可解释、可离线的智能分析是更可行的实现路径")
    for text in [
        "从工程实现视角看，简历评价不是单一的文本分类任务，而是跨越文档接入、文本提取、结构化识别、规则评价、岗位匹配、建议表达和报告生成的复合型问题。如果只强调大模型问答式输出，容易出现结果不稳定、解释不足、现场演示受网络影响等问题。",
        "本项目选择“结构化解析 + 六维评价 + 岗位证据匹配 + 建议生成 + 报告输出 + 三角色协同”的路线，重点强调结果稳定、过程可解释、产物可沉淀、系统可离线演示。平台主链以本地规则与结构化字段为基础，以可选AI增强补充表达能力，既保证了比赛场景的可靠性，也为后续场景扩展留下了技术空间。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    _figure(
        doc,
        FigureItem("图1-1", "三角色协同关系图", "学生端负责上传与优化，教师端负责群体指导，管理端负责平台治理与配置维护。"),
    )
    add_figure_note(doc, "该图强调项目不是单用户工具，而是围绕学生、教师、管理员三类角色组织能力边界。平台的闭环价值，正来源于个体分析结果能够继续流入教师指导与平台治理链路。")

    add_section_heading(doc, 2, "1.2 应用领域场景")
    scenarios = [
        ("1.2.1 面向学生个体的简历优化与岗位准备场景",
         "学生端是平台最直接的服务对象。用户可以上传单份简历，也可以通过ZIP批量上传多份简历样本，围绕目标岗位或岗位模板获得解析、评分、匹配、建议与报告结果。平台把“简历诊断”从主观评价转变为量化与证据并存的结果表达，能够帮助学生在投递前快速完成一轮面向岗位的精细化修订。",
         "与只提供模板参考的工具不同，本项目更关注修改闭环：学生不仅能够看到总分和分项评分，还能看到为什么扣分、哪一段经历缺少量化结果、哪些岗位关键词尚未覆盖以及下一步的行动建议，从而降低反复试错成本。"),
        ("1.2.2 面向教师指导的班级分析与记录回看场景",
         "教师端的价值不在于重复完成学生端已经能自动完成的诊断，而在于把分散的个体分析结果转化为群体性统计。平台能够从班级、专业和年级维度呈现活跃度、平均得分、岗位意向分布和共性问题，使教师能够快速识别需要重点干预的人群和模块。",
         "这意味着教师不必逐份打开简历正文，也能根据汇总数据组织专题指导，例如针对“量化成果表达不足”“岗位意向不明确”“技能栏堆砌但经历支撑不足”等共性问题开展集中辅导，提高有限时间的使用效率。"),
        ("1.2.3 面向学校就业服务数字化建设场景",
         "学校端更关注平台是否具备长期运行和可治理能力。项目已经实现用户管理、配置治理、任务中心、报告中心、审计与存储清理等能力，能够支撑校内就业指导工作从“经验驱动”走向“留痕化、标准化、可复盘”的数字化服务模式。",
         "按照2025年4月8日发布的高质量就业服务体系意见，数字化就业服务已成为高校就业工作的重要方向。本项目在技术边界上保持克制，没有把场景夸大为全能招聘平台，而是聚焦高校毕业生求职前端的简历优化和岗位匹配环节，更贴合校内应用落点。"),
        ("1.2.4 面向比赛展示与成果转化的集中演示场景",
         "比赛作品不仅要解决问题，还要在有限展示时间内让评委快速理解价值、方法和可信度。平台具备学生端主流程、批量分析、教师看板、管理端、报告导出、测试验证和部署说明等多条展示线索，能够在较短时间内构建完整作品感。",
         "从成果转化角度看，平台后续还能沿着职业规划、面试训练、岗位推荐、校企协同和数据分析看板等方向继续演进，因此其价值不止于一次性展示，而具备继续落地与升级的现实基础。"),
    ]
    for title, p1, p2 in scenarios:
        add_section_heading(doc, 3, title)
        add_body_paragraph(doc, p1, first_line=True)
        add_body_paragraph(doc, p2, first_line=True)
    _figure(
        doc,
        FigureItem("图1-2", "平台应用效果路径图", "从学生上传简历到教师回看群体统计，再到学校端形成就业服务资产的完整路径。"),
    )
    add_figure_note(doc, "该图对应应用价值章节中的三层价值结构：学生端形成即时反馈，教师端形成群体洞察，学校端形成标准化资产沉淀。")

    add_section_heading(doc, 2, "1.3 主要工作及创新")
    add_body_paragraph(doc, "本项目围绕高校简历评价与岗位匹配问题，完成了输入接入、结构化解析、评价分析、建议生成、结果展示、工程验证与平台协同等多个层面的工作。相较于只强调某一模型或某一功能的方案，本项目的创新更多体现在“完整闭环 + 解释能力 + 离线稳定 + 平台协同”的综合组织方式上。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表1-2",
            "同类方案与本项目差异对比",
            ["比较维度", "常见简历工具", "本项目平台方案"],
            [
                ["问题边界", "偏重模板推荐或建议生成", "围绕解析、评价、匹配、导出和沉淀构建完整闭环"],
                ["结果形式", "以若干建议文本为主", "评分、证据、建议、任务、报告并存"],
                ["角色体系", "通常只面向学生个人", "覆盖学生、教师、管理员三类角色"],
                ["工程支撑", "较少强调测试与部署说明", "具备自动化测试、CI、部署与安全材料"],
                ["演示稳定性", "依赖外部服务较多", "离线规则主链 + 可选 AI 增强，适合比赛现场演示"],
            ],
        ),
        [2.8, 5.2, 7.8],
    )
    add_table_block(
        doc,
        TableItem(
            "表1-3",
            "项目主要工作与创新归纳",
            ["工作方向", "具体实现", "创新体现"],
            [
                ["文档接入", "多格式上传、ZIP 安全解压、解析质量提示", "覆盖比赛常见输入场景并兼顾安全性"],
                ["评价机制", "结构化解析、六维评价、岗位证据比对", "形成可解释、可复现的分析主链"],
                ["输出表达", "建议生成、报告导出、历史沉淀", "增强成果展示效果与持续使用价值"],
                ["平台协同", "学生端、教师端、管理端统一架构", "体现学校场景中的平台化思路"],
                ["工程支撑", "测试、CI、部署和数据治理材料", "增强项目可信度与交付成熟度"],
            ],
        ),
        [2.6, 6.4, 6.8],
    )

    add_section_heading(doc, 2, "1.4 国内外研究现状综述")
    add_section_heading(doc, 3, "1.4.1 国外研究现状")
    for text in [
        "国外相关研究主要集中在文档解析、岗位与简历匹配、招聘语义理解和可解释推荐等方向。研究重点已经不再停留于关键词重合，而是逐步转向对文档结构、经历表达、技能证据和职位要求之间关系的综合建模。对于复杂版式文档，版面理解和多模态文档解析成为持续关注的技术方向；对于岗位匹配任务，语义检索、证据定位与解释性输出成为提高可用性的关键环节。",
        "这些研究趋势说明，简历评价系统如果只输出一句笼统结论，很难形成真正可用的指导价值。结构化字段、证据片段、量化评分和行动建议的结合，是当前该类应用更可行的发展方向。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_section_heading(doc, 3, "1.4.2 国内研究现状与场景特征")
    for text in [
        "国内相关研究与产品更强调教育服务与求职场景落地，常见方向包括校园就业指导平台、简历解析与推荐服务、岗位推荐与职业规划辅助等。与偏论文型方案相比，国内场景往往更关注系统能否跑通主流程、是否可部署、是否适配高校治理与展示环境。",
        "本项目吸收了上述研究方向中的方法启发，但在实现路径上保持与代码现状一致：文献支撑路线选择，系统现状以规则评价、岗位证据分析、平台协同与工程验证为核心。这种处理方式既能说明方案有研究依据，也能避免理论表述与当前实现能力脱节。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    _figure(
        doc,
        FigureItem("图1-3", "科研支撑到系统实现的映射图", "从文档解析、岗位匹配、可解释建议等研究方向映射到当前平台的具体模块能力。"),
    )
    add_figure_note(doc, "该图用于说明文献综述的作用是支撑路线选择，而不是脱离现有代码实现去堆砌研究热点。每一个研究方向都对应当前仓库中已有的模块落点。")
    doc.add_page_break()


def chapter_two(doc: Document) -> None:
    add_section_heading(doc, 1, "2. 解决方案")
    add_section_heading(doc, 2, "2.1 问题界定")
    for text in [
        "本项目要解决的问题，并不是把简历文件转换成纯文本这么简单，而是围绕高校求职服务构建一条“上传—解析—评价—匹配—建议—导出—沉淀”的完整平台链路。只有把这些环节看作同一系统中的连续步骤，才能解释清楚为什么项目需要工作台、任务中心、报告中心、教师看板和管理后台等平台化组件。",
        "对于学生而言，核心诉求是快速得到可操作的修改方向；对于教师而言，核心诉求是从大量个体结果中提炼群体性问题；对于学校而言，核心诉求是形成可部署、可管理、可维护的就业指导服务系统。三类诉求共同决定了本项目不是单点工具，而是面向高校就业服务的完整平台方案。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表2-1",
            "问题界定与解决思路对应表",
            ["问题类型", "主要表现", "对应解决思路"],
            [
                ["输入问题", "格式多样、批量场景存在安全风险", "建立统一上传校验、ZIP 安全解压与解析入口"],
                ["分析问题", "简历内容难以直接用于岗位比较", "结构化抽取与六维评价并行进行"],
                ["匹配问题", "学生不知道与岗位差距在哪里", "输出缺失关键词、证据片段与行动方向"],
                ["表达问题", "建议零散，难形成成果文档", "生成结果页与 Word/PDF 报告"],
                ["治理问题", "教师与学校难以沉淀记录", "建设教师端、管理员端和报告中心"],
            ],
        ),
        [2.8, 5.2, 7.8],
    )
    add_body_paragraph(
        doc,
        "从评审视角看，这一问题界定还有一层关键含义：项目必须同时回答“为什么要做成平台”和“为什么不是单纯接一个大模型接口”。本项目给出的答案是，简历分析只有在被纳入统一记录主线、任务状态、结果导出和角色权限体系之后，才真正具备持续服务价值。否则，即使某次输出看起来合理，也难以支撑教师指导、群体统计和学校端留痕管理。",
        first_line=True,
    )

    add_section_heading(doc, 2, "2.2 总体方案设计")
    for text in [
        "系统总体方案采用前后端分离架构。前端工作台负责学生、教师和管理员的交互界面；后端服务负责上传接收、分析编排、权限控制和报告生成；数据库与文件目录负责记录沉淀和产物管理；任务层负责批量分析与异步处理。整个系统围绕同一条分析记录主线组织数据流转，避免功能堆叠而缺少中心对象。",
        "在运行策略上，平台以本地规则分析与结构化处理为核心，以可选AI增强为补充。也就是说，系统主流程不把外部调用作为唯一前提，而是优先保证结果可稳定生成、可离线解释并能够在比赛演示环境下顺利运行。只有在用户开启且配置可用时，平台才会进一步调用DeepSeek生成更自然的建议表达、改写预览和面试准备内容。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(
        doc,
        "这一总体方案与高校就业指导场景的契合点在于“主链稳定、增强可选、结果可留”。学生端更关注是否能尽快拿到一份有针对性的分析结论，教师端更关注能否在不直接查看简历全文的情况下获得可用统计，管理端则更关注平台是否能够在多人多角色使用的前提下持续运行。前后端分离和任务中心设计，本质上就是为了同时满足这三类要求。",
        first_line=True,
    )
    _figure(
        doc,
        FigureItem("图2-1", "系统总体架构图", "展示浏览器、API 层、服务层、任务层、数据库与文件存储之间的协同关系。"),
    )
    add_figure_note(doc, "该架构图强调“前端工作台 + 后端服务编排 + 任务中心 + 数据与产物层”的分层方式，适合向评委快速说明系统并非单页脚本，而是可部署的平台结构。")
    _figure(
        doc,
        FigureItem("图2-2", "核心业务流程图", "从用户上传简历、系统解析评分，到报告生成与历史沉淀的完整业务闭环。"),
    )
    add_figure_note(doc, "该流程图服务于问题界定：项目真正解决的是完整业务链问题，而不是只做单次评分。评委可据此快速理解任务中心、报告中心和历史记录为何必要。")

    add_section_heading(doc, 2, "2.3 方案功能")
    add_body_paragraph(doc, "从功能层看，平台由单份分析、批量分析、岗位模板、任务中心、报告中心、教师统计和管理后台七个主要部分组成。每个模块都不是孤立存在，而是围绕统一记录主线和权限体系协同工作，形成比赛展示与持续使用兼顾的产品形态。", first_line=True)
    add_section_heading(doc, 3, "2.3.1 单份分析与结果详情")
    add_body_paragraph(doc, "单份分析是平台最核心、也是最适合比赛现场演示的主流程入口。用户上传DOCX或PDF后，系统立即完成文件校验、文本接入、结构化解析、六维评价、岗位匹配和建议生成，并在结果页中展示总评分、分项评分、解析质量、缺失模块、岗位覆盖率和优先行动清单。与只返回一段大模型文本的工具相比，这一结果页更利于评委快速理解平台到底“分析了什么、为什么这样判断、接下来建议怎么改”。", first_line=True)
    add_body_paragraph(doc, "从仓库实现看，单份分析并不是页面层的简单拼装，而是围绕统一接口、统一记录对象和统一报告产物组织。这种组织方式使得学生修改完简历后能够继续上传新版本并回看历史差异，也使后续教师指导与报告中心共享同一份分析结果，减少逻辑分叉。", first_line=True)
    add_section_heading(doc, 3, "2.3.2 批量分析、岗位模板与任务中心")
    add_body_paragraph(doc, "批量分析用于处理课程作业、班级训练或赛题展示中的多份样本场景。用户上传ZIP包后，系统先完成安全解压和格式过滤，再对每份简历建立独立分析记录，并通过任务中心汇总进度、状态与失败原因。这一机制意味着批量任务不会因为单个坏文件而整体失效，适合答辩时展示平台在更复杂输入条件下的稳定性。", first_line=True)
    add_body_paragraph(doc, "岗位模板模块则用于沉淀目标岗位画像、需求摘要和常见关键词，帮助学生围绕特定岗位开展针对性分析。相比每次手工复制岗位JD，岗位模板更适合学校长期使用，也能让管理端对高频岗位进行统一配置，提升结果的一致性。", first_line=True)
    add_section_heading(doc, 3, "2.3.3 报告中心、教师端与管理端")
    add_body_paragraph(doc, "报告中心承担的是成果化输出角色。平台不仅在网页中展示结果，还会把分析产物转化为Word/PDF报告，支持下载、留档和二次汇报。对学生而言，这意味着分析结论可以直接拿去修改简历；对教师而言，这意味着指导工作不再完全依赖系统在线页面，而有了可以保存和回看的材料载体。", first_line=True)
    add_body_paragraph(doc, "教师端和管理端则体现了项目的平台属性。教师端主要面向群体性洞察，如班级平均分、岗位分布、共性短板和导出能力；管理端主要面向治理能力，如用户状态、AI配置、评分模板、审计日志和文件清理。三者共同构成“个体服务 + 群体指导 + 平台治理”的闭环。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表2-2",
            "功能模块总览",
            ["模块", "核心功能", "主要角色", "作用说明"],
            [
                ["单份分析", "上传、解析、评价、匹配、建议、报告下载", "学生", "完成个体简历评价主流程"],
                ["批量分析", "ZIP 上传、任务状态追踪、结果汇总", "学生/教师", "支撑多份简历批量处理"],
                ["岗位模板", "岗位画像、要求摘要、模板复用", "学生/管理员", "提升分析针对性"],
                ["任务中心", "查看单份与批量任务状态", "学生", "增强流程连续性与可追踪性"],
                ["报告中心", "集中查看与下载 Word/PDF 报告", "学生/教师", "沉淀输出成果"],
                ["教师端", "统计看板、班级分析、学生记录", "教师", "支撑就业指导工作"],
                ["管理端", "用户治理、配置查看、存储清理", "管理员", "保障平台长期运行"],
            ],
        ),
        [2.1, 5.0, 2.2, 6.5],
    )
    add_table_block(
        doc,
        TableItem(
            "表2-3",
            "输入输出与角色边界",
            ["角色", "输入信息", "输出结果", "边界说明"],
            [
                ["学生", "简历文件、目标岗位、岗位 JD、岗位模板", "评分、匹配结果、建议、报告、历史记录", "可查看和管理本人分析数据"],
                ["教师", "班级、专业、年级等筛选条件", "群体统计、学生记录元数据、CSV 导出", "默认不查看学生简历正文"],
                ["管理员", "系统配置、用户角色、存储清理指令", "平台状态、审计日志、用户与记录元数据", "负责平台治理，不参与具体求职分析"],
            ],
        ),
        [2.2, 4.8, 5.0, 3.8],
    )

    add_section_heading(doc, 2, "2.4 赛题要求与系统实现对照")
    add_table_block(
        doc,
        TableItem(
            "表2-4",
            "赛题要求与系统实现对照",
            ["赛题关注项", "当前系统实现", "对应证明材料"],
            [
                ["多格式简历上传与解析", "支持 DOCX、PDF、ZIP，含格式与大小校验", "分析接口、ZIP 服务、测试用例"],
                ["多维度评价与问题诊断", "完成六维评分、诊断建议、结构化问题归纳", "评分引擎、建议引擎、结果页展示"],
                ["岗位匹配分析", "输出岗位关键词覆盖率、缺失要素与证据片段", "匹配引擎、详情页、报告内容"],
                ["可视化报告与导出", "前端图表展示 + Word/PDF 报告导出", "报告服务、ECharts 组件、报告中心"],
                ["工程可信与可部署", "具备测试、CI、Docker、部署说明与安全文档", "pytest 结果、GitHub Actions、部署指南"],
            ],
        ),
        [2.8, 6.0, 6.8],
    )
    add_body_paragraph(doc, "这一对照表的意义，在于把评委最关心的“赛题要求是否真正落到系统实现”直接前置。文稿不试图用宏大叙述替代实现证明，而是把多格式接入、六维评价、岗位匹配、可视化导出和工程可信分别对应到具体模块与材料。这样一来，即便评委不逐页深读，也能在本章末尾快速确认作品不是概念方案，而是已有较完整落地形态的系统。", first_line=True)
    doc.add_page_break()


def chapter_three(doc: Document) -> None:
    add_section_heading(doc, 1, "3. 关键技术")
    add_section_heading(doc, 2, "3.1 文档接入与安全校验")
    for text in [
        "平台输入层支持DOCX、PDF和ZIP三类主要格式。系统在上传阶段对文件后缀、MIME类型和大小进行校验，对ZIP包额外执行路径穿越检查与解压总量限制，以降低恶意压缩包和异常文件带来的运行风险。这一设计直接提升了比赛环境中的稳定性，也为学校场景中的实际使用奠定了安全边界。",
        "对于单份简历，系统会先走统一的文档接入链路，再根据后缀选择DOCX或PDF解析方式。对于批量简历，ZIP文件解压后会自动过滤出支持的文档类型，并对每份简历独立建立记录与结果摘要，避免批量处理过程中出现“一份失败拖垮全包”的情况。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表3-1",
            "文件类型支持与处理方式",
            ["文件类型", "主要处理方式", "边界说明"],
            [
                ["DOCX", "python-docx 读取段落、表格、页眉页脚与 XML 文本补提取", "特殊模板和文本框版式会触发解析质量提示"],
                ["PDF", "pdfplumber 优先提取文本", "扫描版会尝试 OCR 兜底，质量受源文件影响"],
                ["ZIP", "安全解压 + 批量过滤 DOCX/PDF", "限制总大小并拒绝路径穿越内容"],
            ],
        ),
        [2.6, 6.4, 6.6],
    )
    add_body_paragraph(doc, "这一层设计的价值在于，平台在入口阶段就显式区分“可分析”“可部分分析”和“应直接拒绝”的文件，而不是把所有异常都压到后续评分阶段。对比赛作品而言，这能降低演示时因异常文件导致的不可控风险；对长期运行而言，这种先校验、再入链的模式也更符合真实系统的工程习惯。", first_line=True)

    add_section_heading(doc, 2, "3.2 简历结构化解析")
    for text in [
        "结构化解析是平台主链中的核心环节。系统不会把简历简单视为一段长文本，而是优先识别教育背景、实习经历、项目经历、校园实践、技能证书、荣誉奖项、自我评价等模块，并同步提取联系方式、求职意向、关键词、缺失模块和解析告警。这样可以让后续评分、岗位匹配和报告生成都建立在统一的数据结构之上。",
        "在实现层，平台通过标题模式识别、内容线索判断和二次整理机制完成模块归类，并对低质量解析结果进行额外提示。例如，当正文提取过短、核心模块识别不足或特殊版式较多时，系统会标记解析质量为 low 或 medium，防止误导性高分输出。该策略体现了平台对可靠性边界的主动控制。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(doc, "从代码结构看，解析层并不只输出 sections 一个结果，而是同步构造 entities、blocks、missing_sections、warnings 和 confidence 等字段。其中，blocks 用于描述每个板块的预览、行数和识别置信度；missing_sections 用于支撑完整性诊断；warnings 与 parse_warnings 用于在结果页和报告中向用户明确提示风险；confidence 则为后续界面表达“识别较完整/基本识别/识别偏弱”提供依据。", first_line=True)
    add_body_paragraph(doc, "这种输出形式的优势在于，后续模块不需要重新对全文做多次猜测，而是围绕同一套结构化结果展开。评分引擎关注板块是否齐全、证据是否充分，匹配引擎关注岗位关键词与证据片段，报告生成模块则直接把这些中间结果转成面向用户可读的文档内容。结构化解析因此成为整条主链的“共享底座”。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表3-2",
            "结构化识别的核心字段体系",
            ["字段", "含义", "作用"],
            [
                ["raw_text", "完整正文文本", "作为评分、匹配和报告的基础输入"],
                ["sections", "按教育/实习/项目等模块拆分后的结构化结果", "支撑评分与结果展示"],
                ["detected_keywords", "从简历中提取的关键词", "用于岗位匹配和图表摘要"],
                ["detected_target_position", "从简历或文件名中识别的求职意向", "作为岗位匹配辅助输入"],
                ["contact_entities", "邮箱、电话、微信等联系方式实体", "辅助基本信息识别"],
                ["warnings / parse_warnings", "解析告警与质量提示", "控制结果可信边界"],
                ["missing_sections", "缺失的核心模块", "用于生成结构完整性诊断"],
            ],
        ),
        [3.2, 4.2, 7.8],
    )

    add_section_heading(doc, 2, "3.3 六维评价模型")
    for text in [
        "为了避免只给出单一总分、无法指导修改的问题，平台围绕内容完整性、经历相关性、语言专业性、格式规范性、亮点量化程度和岗位语义匹配六个维度构建评价体系。每个维度不仅有独立评分，还对应明确的证据逻辑、诊断触发条件和建议生成方向。",
        "在权重设计上，平台默认模板强调内容完整性、经历相关性和岗位匹配三项核心因素，同时支持按岗位类型切换权重模板。例如，数据分析岗更强调岗位匹配与亮点量化，前后端开发岗更强调经历相关性与岗位匹配。这种设计既保证了统一评价主线，又为不同岗位场景保留了差异化空间。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(doc, "更重要的是，这六个维度不是独立漂浮的标签，而是可以追溯到具体证据逻辑。例如，经历相关性会参考 experience_line_count、action_line_count 和 result_line_count；亮点量化程度会参考 metric_line_count 和 sample_metric_lines；岗位语义匹配则会结合 matched_keywords、missing_keywords 与 match_rate。评委因此可以相信，这套评分不是凭空给分，而是由可查看、可复盘的规则链支撑。", first_line=True)
    _figure(
        doc,
        FigureItem("图3-1", "六维评价模型图", "展示六个核心维度之间的关系、权重结构以及从结构化字段到结果输出的映射方式。"),
    )
    add_figure_note(doc, "该图说明评分不是单一黑盒总分，而是由六个具有不同证据依据的维度共同组成。后续建议、匹配摘要与行动路线图都围绕这套维度体系展开。")
    add_table_block(
        doc,
        TableItem(
            "表3-3",
            "六维评价维度及依据",
            ["维度", "主要依据", "结果作用"],
            [
                ["内容完整性", "是否覆盖教育、实习、项目、技能等核心模块", "判断简历结构是否完整"],
                ["经历相关性", "经历条目数量、行动词、结果闭环和项目/实习支撑情况", "衡量经历是否足以证明能力"],
                ["语言专业性", "动作表达、泛化词数量、长句情况", "评估表述是否专业、简洁"],
                ["格式规范性", "板块结构、联系方式、日期线索、平均句长", "判断整体可读性与规范程度"],
                ["亮点量化程度", "阅读量、转化率、处理量、完成量等指标表达", "衡量成果说服力"],
                ["岗位语义匹配", "目标岗位关键词覆盖率、缺失关键词、证据片段", "评估简历与目标岗位的适配程度"],
            ],
        ),
        [2.6, 6.2, 6.8],
    )

    add_section_heading(doc, 2, "3.4 岗位匹配与证据分析")
    for text in [
        "岗位匹配模块并不只输出一个抽象匹配度，而是基于目标岗位名称、岗位JD与岗位画像，构建 must / nice 两级关键词集合，并结合简历文本命中情况形成覆盖率、缺失词与证据片段。系统还会自动识别部分岗位类型，如数据分析、产品经理、前端开发、后端开发和新媒体运营等，以增强岗位匹配的业务针对性。",
        "与只统计关键词命中次数的方式相比，本项目更强调证据表达。系统会优先输出与岗位最相关的简历片段，帮助学生理解“哪些内容已经构成优势”“哪些能力尚未被写出来”，也帮助教师和评委快速判断匹配结果是否可信。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(doc, "从输出字段看，岗位匹配结果不仅包含 score 和 summary，还包含 target_source、profile、match_rate、confidence 与 evidence_snippets。target_source 用于区分岗位是手动输入、简历识别还是通用规则；confidence 用于控制结果表达强弱；evidence_snippets 则直接把命中的简历片段回传给前端和报告模块。这种设计使“匹配分析”从抽象分数转化为可被验证的证据型结果。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表3-4",
            "岗位匹配结果输出字段",
            ["字段", "说明"],
            [
                ["score", "岗位匹配分数"],
                ["target_position / target_source", "目标岗位及来源（手动输入、简历识别或通用规则）"],
                ["matched_keywords", "已匹配关键词列表"],
                ["missing_keywords", "缺失关键词列表"],
                ["evidence_snippets", "与岗位要求最相关的证据片段"],
                ["confidence", "匹配置信度"],
                ["match_rate", "关键词覆盖率"],
                ["summary", "岗位匹配摘要描述"],
            ],
        ),
        [3.8, 11.8],
    )

    add_section_heading(doc, 2, "3.5 AI 增强与离线回退")
    for text in [
        "平台中的DeepSeek能力被设计为增强层，而不是主流程唯一前提。对于能够正常识别正文、且用户主动开启AI增强的场景，系统会在规则评分和结构化结果基础上生成更自然的诊断表达、改写预览和面试准备内容；当API不可用、网络受限或用户关闭AI时，系统则自动回退到离线规则分析。",
        "这种“规则主链 + 可选AI增强”的架构有两个直接好处：第一，比赛环境中即使没有稳定外网，也可以完整演示主流程；第二，评分与建议的基础逻辑可解释、可追溯，不会因为大模型随机性导致结果漂移。对于高校落地场景，这种设计也更符合数据安全与稳定运行要求。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(doc, "在实现层面，系统会根据 parse_quality、batch_file_count 和用户开关决定是否尝试增强。若正文提取质量过低、批量任务过多或外部服务不可用，平台会跳过增强流程并记录 ai_skip_reason，必要时标记 analysis_mode 为 offline_fallback。这样做的价值不是“弱化AI”，而是把AI放在可控的位置上，让它为表达质量服务，而不是决定主链是否能够工作。", first_line=True)

    add_section_heading(doc, 2, "3.6 报告生成与可视化展示")
    for text in [
        "在结果展示层，平台通过ECharts输出分项评分、雷达图和统计可视化，同时支持生成Word和PDF报告。单份分析场景中，Word报告可即时生成，PDF报告可在下载时按需生成；批量分析场景中，平台会为每份简历形成独立结果，并提供汇总视图和任务状态追踪能力。",
        "报告结构围绕总评分、分项得分、问题诊断、修改建议、岗位匹配摘要和结构化建议展开，既方便学生修改简历，也利于教师指导和比赛展示。相较于只呈现网页结果，报告中心显著增强了成果留存与材料化输出能力。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(doc, "报告模块的另一个亮点在于，它把网页结果中的结构化建议、匹配摘要和解析质量一并转译到文档中，而不是只导出一个简化分数页。对于比赛场景，这意味着评委即使不在浏览器中操作，也能通过报告材料快速把握平台输出的细度；对于高校场景，这意味着学生和教师可以离线共享分析结论，降低平台在线依赖。", first_line=True)

    add_section_heading(doc, 2, "3.7 平台工程支撑与可信验证")
    for text in [
        "截至2026年8月3日，平台后端已形成14个API层模块、26个服务层模块，前端包含15个主要页面视图。项目采用FastAPI、SQLAlchemy、Vue 3、Vite、MySQL、Redis和Celery等技术栈完成平台组织，既覆盖基础分析链路，也覆盖任务、报告、教师端和管理端功能。",
        "工程可信度方面，项目后端测试目录共包含25个测试文件、107个测试函数。2026年8月3日本机执行pytest结果为107 passed、122 warnings；GitHub Actions配置同时包含后端自动化测试和前端生产构建；同日执行npm run build，Vite完成2161个模块转换并成功生成dist产物。测试与构建材料说明平台并非概念演示，而具备真实可运行与可验证的工程基础。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(doc, "若进一步拆开看，工程支撑至少覆盖四个层面：一是后端服务层模块化，说明功能并非写在单一脚本中；二是前端页面与工作台组织，说明作品具备完整交互形态；三是自动化测试和CI，说明关键能力具备回归验证基础；四是部署指南、Nginx 示例、Docker Compose 和数据安全说明，说明项目已经考虑到“如何跑起来、如何被管理、如何控制边界”。对于参赛文档而言，这些支撑共同构成了评委判断“是不是空壳项目”的重要依据。", first_line=True)
    _figure(
        doc,
        FigureItem("图3-2", "比赛演示流程图", "展示从注册或游客访问、上传简历、查看结果，到下载报告和教师回看统计的演示顺序。"),
    )
    add_figure_note(doc, "该图对应答辩路径设计。对于比赛展示，按“进入系统—上传样本—查看结果—展示报告—切换教师端”的顺序，最容易让评委在短时间内建立完整理解。")
    _figure(
        doc,
        FigureItem("图3-3", "数据流与安全边界图", "展示本地上传、解析、评分、报告与可选外部 AI 调用之间的数据流向与边界控制。"),
    )
    add_figure_note(doc, "该图的重点不是画复杂流向，而是清楚表达：规则主链默认在本地闭环，AI 增强只有在显式开启且配置可用时才触发，并且失败时自动回退为 offline_fallback。")
    _figure(
        doc,
        FigureItem("图3-4", "任务处理流程图", "展示单份分析、批量分析、异步任务与报告生成之间的任务编排关系。"),
    )
    add_figure_note(doc, "该图帮助评委理解任务中心存在的意义。单份与批量分析、即时结果与报告生成、同步路径与异步路径都围绕统一任务对象组织。")
    _figure(
        doc,
        FigureItem("图3-5", "项目可信性来源结构图", "从测试、CI、部署、数据治理和离线回退机制等维度展示项目可信性来源。"),
    )
    add_figure_note(doc, "该图起到技术章和附录之间的桥梁作用，把“为什么可信”从文字表述转化为结构性说明，便于评委在阅读后续附录时形成映射。")
    add_table_block(
        doc,
        TableItem(
            "表3-5",
            "技术选型与作用",
            ["层级", "选型", "作用"],
            [
                ["前端框架", "Vue 3 + Vite + Vue Router", "构建工作台、页面导航与结果展示"],
                ["可视化", "ECharts", "实现评分图表与统计看板"],
                ["后端框架", "FastAPI + Uvicorn", "提供分析、鉴权和治理 API"],
                ["数据持久化", "SQLAlchemy + MySQL", "管理用户、记录、任务和报告元数据"],
                ["文档解析", "python-docx、pdfplumber、可选 PaddleOCR", "处理简历正文接入与 OCR 兜底"],
                ["异步任务", "Redis + Celery", "支持任务中心与批量分析处理"],
                ["报告输出", "python-docx、reportlab", "生成 Word/PDF 报告"],
            ],
        ),
        [2.8, 4.8, 7.2],
    )
    add_table_block(
        doc,
        TableItem(
            "表3-5-扩",
            "后端服务模块与职责摘要",
            ["服务模块", "主要职责"],
            get_service_module_rows_split()[0],
        ),
        [5.0, 9.8],
    )
    add_table_block(
        doc,
        TableItem(
            "表3-5-续",
            "后端服务模块与职责摘要（续）",
            ["服务模块", "主要职责"],
            get_service_module_rows_split()[1],
        ),
        [5.0, 9.8],
    )
    add_table_block(
        doc,
        TableItem(
            "表3-6",
            "测试与构建现状归纳",
            ["项目", "当前结果"],
            [
                ["后端测试文件数", "17 个"],
                ["测试函数数", "107 个"],
                ["最新 pytest 结果", "107 passed, 122 warnings（2026-08-03）"],
                ["CI 配置", "后端 pytest + 前端 build 双流水线"],
                ["前端构建结果", "Vite 构建成功，2161 modules transformed"],
                ["后端路由规模", "58 条应用路由"],
            ],
        ),
        [5.0, 10.5],
    )
    add_table_block(
        doc,
        TableItem(
            "表3-7",
            "分析结果关键字段样例",
            ["字段", "示例值", "说明"],
            [
                ["parse_quality", "medium", "解析质量等级"],
                ["missing_sections", "['projects']", "未识别到的核心板块"],
                ["match_rate", "67", "岗位关键词覆盖率"],
                ["confidence", "0.78", "岗位匹配置信度"],
                ["analysis_mode", "core / offline_fallback", "主链或回退模式"],
                ["action_roadmap", "优先补齐项目经历、补充SQL关键词", "结果页优先行动清单"],
            ],
        ),
        [3.6, 4.8, 6.4],
    )

    add_section_heading(doc, 2, "3.8 典型案例页：从输入到报告输出的完整链路")
    add_body_paragraph(doc, "为了让平台能力更具象地被理解，可以用一份面向“数据分析岗”或“新媒体运营岗”的示例简历演示整条链路：用户上传DOCX/PDF文件后，系统首先完成文本接入与结构化拆解，识别教育背景、项目经历、技能证书与求职意向；随后根据岗位画像生成六维得分和岗位关键词覆盖率；接着输出问题诊断、缺失能力和行动建议；最后生成Word/PDF报告并沉淀到历史中心。该流程说明平台不是多个孤立功能的拼接，而是完整业务闭环。", first_line=True)
    add_quote_box(
        doc,
        "案例链路摘要",
        "输入：简历文件 + 目标岗位；中间结果：sections、keywords、match_result、structured_suggestions；输出：评分图表、岗位摘要、建议列表、报告文件与历史记录。",
    )
    add_body_paragraph(doc, "如果以一份数据分析岗简历为例，系统可能会识别出“缺少 SQL、数据清洗、可视化”等岗位关键词，发现项目经历中存在行动词但量化结果不足，进而在建议层给出“补充处理数据量、模型指标或业务效果”的方向。这样的链路尤其适合答辩展示，因为它既能让评委看到结构化解析结果，又能让评委直接理解评分与建议为什么会产生。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表3-8",
            "案例链路分阶段输出示意",
            ["阶段", "系统输出", "评审可观察点"],
            [
                ["输入阶段", "上传 DOCX/PDF、岗位名称或 JD", "支持多格式与岗位信息输入"],
                ["解析阶段", "sections、entities、missing_sections、warnings", "结构化识别是否真实可解释"],
                ["评价阶段", "总评分、六维分项、解析质量", "是否不是单一总分黑盒"],
                ["匹配阶段", "match_rate、missing_keywords、evidence_snippets", "岗位差距是否可见"],
                ["建议阶段", "structured_suggestions、action_roadmap", "建议是否可执行"],
                ["产物阶段", "Word/PDF 报告、历史记录、任务中心状态", "结果是否可沉淀与复用"],
            ],
        ),
        [2.8, 6.2, 6.0],
    )
    add_body_paragraph(doc, "对评委而言，这一案例页最重要的意义不是展示“某一份简历得了多少分”，而是展示平台从输入到输出之间的每一步都可被理解、可被追踪、可被复核。也正因为如此，本项目更适合被理解为一个具备完整工程闭环的高校就业指导工具，而不是一次性调用外部模型得到结果的演示脚本。", first_line=True)
    add_section_heading(doc, 2, "3.9 结果样例与可解释输出")
    add_body_paragraph(doc, "参赛作品是否容易得高分，很大程度上取决于评委能否在短时间内看懂输出结果。本项目在结果表达层刻意避免“一个总分 + 一段长文本”的单薄形式，而是把解析质量、六维分项、岗位覆盖率、缺失模块、证据片段、结构化建议和行动路线图拆成多个信息块并行展示。这样做的目的，是让不同关注点的评审都能迅速找到自己最关心的证据。", first_line=True)
    add_body_paragraph(doc, "例如，关注技术实现的评委会优先看结构化字段、match_rate 和 evidence_snippets；关注场景价值的评委会优先看 action_roadmap 和报告输出；关注工程可信度的评委会则会结合 parse_warnings、analysis_mode 与后续附录中的测试和接口材料进行判断。结果页因此既是用户交互界面，也是作品解释结构的一部分。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表3-9",
            "结果页关键信息块与展示作用",
            ["信息块", "主要内容", "展示作用"],
            [
                ["总评分", "0-100 综合得分与等级标签", "快速建立整体印象"],
                ["六维分项", "完整性、经历、语言、格式、亮点、岗位匹配", "展示不是单一打分黑盒"],
                ["解析质量", "high / medium / low 与告警信息", "明确边界与可信度"],
                ["岗位匹配卡", "match_rate、missing_keywords、evidence_snippets", "说明与岗位差距在哪里"],
                ["结构化建议", "problem / evidence / direction / example", "把建议从泛建议升级为证据型建议"],
                ["行动路线图", "优先级、标题、处理方向", "帮助用户按先后顺序修改"],
            ],
        ),
        [2.8, 6.0, 6.2],
    )
    add_table_block(
        doc,
        TableItem(
            "表3-10",
            "报告内容组成与使用对象",
            ["报告组成", "主要内容", "主要使用对象"],
            [
                ["首页摘要", "文件名、时间、分析模式、解析质量", "学生/教师/评委"],
                ["评分页", "总评分与六维分项得分", "学生/评委"],
                ["诊断页", "问题诊断与缺失模块说明", "学生/教师"],
                ["建议页", "建议列表与结构化建议", "学生/教师"],
                ["岗位匹配页", "目标岗位、覆盖率、关键词缺口", "学生/评委"],
                ["结论页", "修改重点与下一步行动方向", "学生/教师"],
            ],
        ),
        [2.8, 6.0, 6.2],
    )
    add_body_paragraph(doc, "这一节的意义在于，把“结果为什么看起来完整”也解释清楚。平台不是把内部字段直接堆到页面上，而是围绕用户决策顺序组织信息层次：先看是否值得投递，再看差距在哪里，再看应该如何修改，最后看如何沉淀为可下载的成果文档。这种结构既适合真实用户使用，也适合比赛演示。", first_line=True)
    add_section_heading(doc, 2, "3.10 稳定性策略与异常处理")
    add_body_paragraph(doc, "对于参赛系统而言，稳定性不只是“功能能跑起来”，还包括在异常输入、弱网络、批量场景和低质量文件条件下，系统是否仍能给出可解释、可控的输出。本项目在主链设计中把这种稳定性看作与评分能力同样重要的组成部分，因此在上传校验、解析质量标注、AI调用开关、批量任务策略和文件清理机制上都做了显式边界控制。", first_line=True)
    add_body_paragraph(doc, "具体来说，当正文提取不足时，系统会优先降低 parse_quality 并提示用户重传标准文件，而不是硬算一个看似完整的高分；当外部AI不可用时，系统会直接回退为 offline_fallback，保证主流程仍然完成；当批量任务规模过大时，系统则优先选择更稳的规则主链，以换取更可控的时延和完成率。这样的处理逻辑虽然看上去“保守”，但恰恰更适合比赛答辩和高校实际落地。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表3-11",
            "稳定性策略与对应机制",
            ["稳定性目标", "对应机制", "作用说明"],
            [
                ["异常文件可控", "格式校验、大小限制、ZIP 安全解压", "降低入口阶段风险"],
                ["低质量解析可见", "parse_quality + parse_warnings", "防止误导性结果"],
                ["主流程不依赖外网", "规则主链默认可独立运行", "保障比赛现场稳定性"],
                ["AI 服务可选可退", "enable_ai 开关 + offline_fallback", "兼顾增强效果与可靠性"],
                ["批量任务可追踪", "任务中心 + 状态查询 + 重试/暂停接口", "提升大样本处理可控性"],
                ["运行期文件可回收", "删除记录联动清理上传、解压、报告文件", "控制存储生命周期"],
            ],
        ),
        [3.0, 5.2, 6.8],
    )
    add_body_paragraph(doc, "从评审角度看，这一节能够帮助作品和普通“调用接口型应用”拉开差距。真正的平台型作品不仅要展示成功路径，还要证明自己考虑过失败路径，并且在失败时依然知道该怎么优雅地退回到可接受状态。", first_line=True)
    doc.add_page_break()


def chapter_four(doc: Document) -> None:
    add_section_heading(doc, 1, "4. 应用价值")
    add_section_heading(doc, 2, "4.1 学生端价值")
    for text in [
        "平台对于学生最直接的价值在于缩短简历修改周期。传统模式下，学生往往需要先写一版简历，再等待教师或同伴反馈，再按经验模糊修改；平台将这一过程改写为结构化反馈链路，使学生能够在提交前快速获得问题定位、量化结果和改写方向。",
        "由于平台支持岗位模板和岗位证据匹配，学生可以围绕目标岗位构建多版本简历，不再停留在“一个简历投所有岗位”的粗放方式。报告中心和历史记录还能帮助学生回看不同版本之间的得分变化，使求职准备过程更有条理。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(doc, "从价值密度看，学生端最大的提升不只是“快”，而是“快且知道为什么”。平台把简历问题拆成完整性、经历、语言、格式、亮点和岗位匹配六类，使学生在第一次查看结果时就能明确哪些问题应该先改、哪些问题可以后改。对毕业季时间紧、投递频率高的用户来说，这种优先级感本身就是非常实际的价值。", first_line=True)
    add_section_heading(doc, 2, "4.2 教师端价值")
    for text in [
        "教师端的价值体现在将个体辅导升级为群体诊断。平台通过统计看板、班级分析和学生记录元数据输出，把原本分散的简历质量问题转化为可汇总、可比较的图表与列表，使教师能够更精准地识别共性短板并组织集中指导。",
        "这种模式并不是要替代教师，而是把教师从重复性、低沉淀度的初步筛查工作中解放出来，使其把时间投入到更需要经验判断和深度辅导的环节，从而提升就业指导效率和覆盖面。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(doc, "尤其在毕业季集中指导场景中，教师往往最缺的不是专业经验，而是快速把经验作用到大样本中的工具。教师端提供的班级、专业、年级等聚合视角，可以把个体问题转化为专题辅导议题，例如“项目经历缺少量化表达”“求职意向表述不清”“技能栏堆砌但经历支撑不足”。这种转化能力使平台真正融入指导流程，而不只是一个学生自助工具。", first_line=True)
    add_section_heading(doc, 2, "4.3 学校端价值")
    for text in [
        "对学校而言，平台体现的是就业服务数字化、标准化和可复盘价值。系统不仅可以生成学生个体层面的分析结果，还能沉淀历史记录、报告文件、任务状态和统计元数据，为后续就业服务优化、课程设计和指导资源配置提供参考依据。",
        "结合2025年4月8日发布的高质量就业服务体系意见，数字化就业服务已经成为高校就业工作的重要方向。本项目聚焦简历分析这一切入点，能够以较低成本支撑高校就业服务的部分数字化建设目标。",
    ]:
        add_body_paragraph(doc, text, first_line=True)
    add_body_paragraph(doc, "从学校治理角度看，平台更大的意义在于形成标准化流程。过去大量简历指导工作往往依赖老师个人经验和线下沟通，难以留痕、难以统计，也难以形成可复用的方法资产。平台把上传、分析、建议、导出和回看放在同一系统内完成后，学校便可以逐步沉淀属于自身场景的岗位模板、指导经验和统计口径。", first_line=True)
    add_section_heading(doc, 2, "4.4 展示与推广价值")
    add_body_paragraph(doc, "从比赛展示角度看，项目同时具备问题真实、功能完整、图表清晰、工程可信和材料充分等特点，能够在较短答辩时间内完整呈现价值、方案与实现路径。从后续推广角度看，平台还可沿着职业规划、岗位推荐、面试训练、校企协同和数据分析看板等方向继续扩展，具备较强的成果转化潜力。", first_line=True)
    add_body_paragraph(doc, "这也是本项目更适合采用“价值为主，技术为证”表达方式的原因。它并不是某个孤立模型精度的展示，而是围绕真实场景组织出来的一套平台能力。只要评委能在前几页看清问题、在中间章节看清实现、在附录看清验证，就更容易形成“作品完整度高、落地可能性强”的整体印象。", first_line=True)
    _figure(
        doc,
        FigureItem("图4-1", "平台应用效果路径图", "展示学生、教师和学校三个层面的应用效果与价值传递路径。"),
    )
    add_figure_note(doc, "价值章节中的图不追求复杂技术信息，而是帮助评委把价值落点与角色场景直接对应起来。")
    _figure(
        doc,
        FigureItem("图4-2", "比赛展示流程图", "展示从功能演示、图表展示到工程验证与价值总结的答辩路径。"),
    )
    add_figure_note(doc, "该图提示的是“如何讲作品”，与前文的业务流程不同，它服务于答辩表达的节奏组织。")
    add_table_block(
        doc,
        TableItem(
            "表4-1",
            "不同用户对象收益表",
            ["对象", "主要收益"],
            [
                ["学生", "缩短修改周期、提高岗位针对性、形成报告化成果"],
                ["教师", "从逐份辅导转向群体诊断、提升指导效率"],
                ["学校", "推动就业服务数字化、标准化与可复盘"],
            ],
        ),
        [2.6, 12.8],
    )
    add_table_block(
        doc,
        TableItem(
            "表4-2",
            "推广应用场景表",
            ["场景", "可扩展方向"],
            [
                ["校内就业指导", "班级分析、专题辅导、优秀案例沉淀"],
                ["课程教学", "简历写作、岗位认知、职业素养训练"],
                ["校企协同", "岗位模板共享、定向岗位指导"],
                ["比赛展示", "主流程演示、测试与部署证明、平台能力展示"],
            ],
        ),
        [3.0, 12.4],
    )
    add_section_heading(doc, 2, "4.5 比赛适配度与评审响应")
    add_body_paragraph(doc, "从比赛评审逻辑看，高分作品通常同时具备四类特征：问题真实、方案完整、技术可信、价值明确。本项目在这四个维度上都具备相对均衡的表现。问题层面，项目聚焦高校毕业生简历优化这一真实且高频的痛点；方案层面，项目把上传、解析、评价、匹配、建议、导出和沉淀组织成完整闭环；技术层面，项目以规则主链、结构化字段、测试与部署材料构成可信支撑；价值层面，项目同时覆盖学生、教师和学校三类角色。", first_line=True)
    add_body_paragraph(doc, "这意味着作品并不依赖某一项单点亮眼指标取胜，而是依靠整体完成度建立竞争力。对评委而言，这类作品的优势在于理解成本低、答辩可验证点多、材料之间能互相印证，不容易出现“讲得很好但落不到系统里”的断层。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表4-3",
            "比赛评审关注点与项目响应关系表",
            ["评审关注点", "项目响应方式", "对应章节/材料"],
            [
                ["问题是否真实", "基于2025-2026年就业政策与毕业生规模背景切入", "第1章、参考文献"],
                ["功能是否完整", "形成从上传到报告沉淀的完整闭环", "第2章、图2-2"],
                ["技术是否可信", "规则主链、字段结构、测试构建、部署材料", "第3章、附录A/B/C"],
                ["价值是否清晰", "学生、教师、学校三层价值对应", "第4章、图4-1"],
                ["未来是否可扩展", "沿解析、匹配、治理与求职服务链持续扩展", "第5章、图5-1"],
            ],
        ),
        [3.2, 5.6, 6.0],
    )
    add_body_paragraph(doc, "因此，本项目的比赛适配度并不只体现在“有页面、有接口、有图表”，而体现在作品叙事与系统实现之间保持一致：文档中强调的每一条亮点，基本都能在仓库结构、接口设计、测试结果或部署材料中找到对应证据。", first_line=True)
    doc.add_page_break()


def chapter_five(doc: Document) -> None:
    add_section_heading(doc, 1, "5. 系统优化与展望")
    add_section_heading(doc, 2, "5.1 当前局限性")
    add_body_paragraph(doc, "尽管平台已经形成较为完整的功能闭环，但从真实运行边界看，仍存在若干需要持续优化的方面。首先，复杂版式简历、文本框模板和图片化内容会对解析稳定性造成影响，即使系统已经增加XML补提取和解析质量提示，仍不能完全替代对标准化文档的需求。其次，扫描件识别依赖OCR质量，当源文件清晰度较低、版式复杂或中英文混排较多时，识别结果可能受到影响。再次，岗位匹配当前仍以规则与关键词证据分析为主，虽然已能提供较强解释性，但在更复杂的语义推断场景中仍有进一步提升空间。最后，教师端和学校端当前已能提供统计与治理能力，但在更深层次的就业趋势分析和分层推荐方面仍有后续拓展空间。", first_line=True)
    add_body_paragraph(doc, "这些局限性在文稿中被明确写出，而不是被回避，原因在于高质量参赛作品不应把“尚未解决的问题”包装成“已经解决”。对评委而言，能够清晰划定当前边界、说明为什么会有这个边界、再指出下一步迭代方向，往往比不加区分地拔高能力更有说服力。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表5-1",
            "当前局限性与改进方向对照",
            ["当前局限性", "改进方向"],
            [
                ["复杂版式简历解析边界仍然存在", "引入更强的版面理解与多模态解析能力"],
                ["OCR 对扫描件质量依赖较强", "增强文字检测与清洗策略"],
                ["岗位匹配以规则和关键词证据为主", "进一步补充语义检索与重排机制"],
                ["教师端统计能力仍偏基础", "增强群体分析、趋势分析与分层指导能力"],
            ],
        ),
        [7.3, 8.1],
    )
    add_section_heading(doc, 2, "5.2 未来展望")
    add_body_paragraph(doc, "未来，平台可沿着四条主线继续演进：一是增强文档解析能力，在复杂版式、扫描件与作品集类简历处理中提升稳定性；二是增强岗位匹配能力，在现有证据匹配基础上引入更强的语义检索与岗位分类策略；三是增强治理能力，通过更完整的任务监控、审计和配置体系支撑长期运行；四是增强求职服务链路，在简历分析之外延伸到面试训练、职业规划和校企协同等更完整的服务场景。总体来看，项目的后续优化不是推倒重来，而是在现有平台骨架上沿着“更强解析—更强匹配—更强治理—更完整服务”这条主线持续迭代。", first_line=True)
    add_body_paragraph(doc, "如果从成果转化角度看，后续最具价值的升级方向是把现有简历分析结果进一步连接到职业准备全链路，例如基于岗位模板自动推荐面试准备路径、根据群体短板生成课程化训练主题、围绕校企合作岗位建立专门的画像模板等。这样一来，项目的定位将从“简历评价平台”自然延伸到“高校求职准备支撑平台”，但其核心骨架仍然沿用当前已经跑通的分析主链。", first_line=True)
    add_section_heading(doc, 2, "5.3 后续实施路径")
    add_body_paragraph(doc, "若将项目从比赛作品进一步推进到校内试运行，建议采用“小范围试点—规则校准—角色扩展—服务延伸”的分阶段策略。第一阶段围绕一个学院或一个专业开展试点，重点验证模板设置、岗位画像和教师统计口径是否贴合真实指导流程；第二阶段基于试点结果校准评分模板和建议表达；第三阶段再逐步引入更多教师角色、更多岗位模板和更完整的治理配置。", first_line=True)
    add_body_paragraph(doc, "这种路径的优势在于，不需要等待“所有能力都极其完善”后再启动应用，而是可以依靠当前已经成熟的主链能力先形成可见价值，再在使用过程中持续增强复杂解析、语义匹配和课程化支撑能力。对成果转化而言，这比一次性追求大而全更可行。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表5-2",
            "后续实施路径建议表",
            ["阶段", "重点任务", "目标结果"],
            [
                ["试点阶段", "围绕少量班级或专业上线试用", "验证主链流程和教师统计口径"],
                ["校准阶段", "优化岗位模板、评分权重和建议表达", "提升结果针对性与可接受度"],
                ["扩展阶段", "接入更多角色、岗位模板和治理配置", "形成校内可复用平台能力"],
                ["延伸阶段", "连接面试训练、职业规划和校企协同", "拓展为更完整求职服务链路"],
            ],
        ),
        [3.0, 6.0, 5.8],
    )
    _figure(
        doc,
        FigureItem("图5-1", "当前能力与未来扩展路线图", "围绕解析、匹配、治理和求职服务链路展示平台演进方向。"),
    )
    add_figure_note(doc, "路线图强调项目未来演进是在现有骨架上增强，而不是另起炉灶。这样既体现扩展潜力，也保持与当前实现的一致性。")
    _figure(
        doc,
        FigureItem("图5-2", "项目可信性来源结构图", "从政策背景、代码实现、测试、构建、部署和安全治理等维度总结项目可信性。"),
    )
    add_figure_note(doc, "该图在展望章节再次出现，是为了把“当前可信”与“未来可持续扩展”联系起来，突出项目并非只适用于一次比赛展示。")
    doc.add_page_break()


def references(doc: Document) -> None:
    add_section_heading(doc, 1, "参考文献")
    refs = [
        "新华社. 2026届全国普通高校毕业生规模预计1270万人[EB/OL]. 2025-11-20. https://www.news.cn/20251120/ead0f25dff2948dfa7f01fa78f207882/c.html",
        "中共中央办公厅、国务院办公厅. 关于加快构建普通高等学校毕业生高质量就业服务体系的意见[EB/OL]. 2025-04-08. https://www.moe.gov.cn/jyb_xxgk/moe_1777/moe_1778/202504/t20250408_1186543.html",
        "教育部办公厅、人力资源社会保障部办公厅. 关于开展2026年高校毕业生就业政策宣传活动的通知[EB/OL]. 2026-04-23. https://www.moe.gov.cn/srcsite/A15/s3265/202604/t20260423_1434600.html",
        "教育部. 教育部部署2026届高校毕业生就业“百日冲刺”行动[EB/OL]. 2026-06-08. https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/s5987/202606/t20260608_1439860.html",
        "国家大学生就业服务平台[EB/OL]. https://www.ncss.cn/",
        "国家大学生就业服务平台. 2026届高校毕业生全国网络联合招聘[EB/OL]. https://www.ncss.cn/student/24365",
        "Xu Y, et al. LayoutLM: Pre-training of Text and Layout for Document Image Understanding[EB/OL]. arXiv.",
        "相关项目源码、测试结果、部署说明与安全文档，均来自本项目仓库截至2026-06-30的本地实测与归档材料。",
    ]
    for ref in refs:
        add_body_paragraph(doc, ref)
    doc.add_page_break()


def appendix_a(doc: Document) -> None:
    add_section_heading(doc, 1, "附录A 测试验证与支撑材料")
    add_body_paragraph(doc, "本项目测试材料用于证明平台不是概念演示，而是具备真实可运行、可验证和可回归的工程基础。后端测试目录包含17个测试文件、68个测试函数，覆盖解析器、流水线、权限、异步分析、批量处理、教师端、模板推荐和面试模块等主要能力。", first_line=True)
    add_body_paragraph(doc, "截至2026年8月3日本机实测，后端执行 pytest 结果为 107 passed、122 warnings；同日前端执行 npm run build 成功，Vite 构建阶段共完成 2161 个模块转换并生成 dist 产物；仓库同时包含单个 ci.yml 工作流，对 push 至 main/master 与 pull request 执行后端测试与前端构建。以上材料共同构成了“本地实测 + 仓库自动验证”的双重支撑。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表A-1",
            "测试文件与用例统计表",
            ["项目", "数值"],
            [
                ["测试文件数", "17"],
                ["测试函数数", "68"],
                ["最新 pytest 结果", "107 passed, 122 warnings"],
                ["测试总耗时", "以答辩前最后一次本机实测为准"],
            ],
        ),
        [5.5, 10.0],
    )
    add_table_block(
        doc,
        TableItem(
            "表A-1-扩",
            "测试文件覆盖明细",
            ["测试文件", "主要主题", "测试函数数"],
            get_test_file_breakdown(),
        ),
        [4.3, 7.8, 3.2],
    )
    add_table_block(
        doc,
        TableItem(
            "表A-1-类",
            "测试类别统计",
            ["测试类别", "测试函数数"],
            get_test_category_breakdown(),
        ),
        [8.0, 6.0],
    )
    add_table_block(
        doc,
        TableItem(
            "表A-2",
            "测试与构建结论汇总",
            ["验证项", "结论"],
            [
                ["后端自动化测试", "通过"],
                ["前端生产构建", "通过"],
                ["CI 配置", "已配置单个 ci.yml，分别执行后端 pytest 与前端 build"],
                ["平台主流程", "支持单份分析、批量分析、报告导出、教师端和管理端场景"],
            ],
        ),
        [6.2, 9.3],
    )
    add_body_paragraph(doc, "从测试组织方式上看，项目并不是只围绕某一个算法函数写少量单元测试，而是覆盖了解析、评分、匹配、异步、批量、教师端、模板和增强能力等多个横向模块。这意味着平台在展示时的稳定性更多来自系统性验证，而不是“现场刚好没有出错”。对于参赛文档，这样的证明方式比单纯展示几张成功截图更有说服力。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表A-3",
            "验证口径与材料来源对应表",
            ["验证口径", "当前结论", "来源说明"],
            [
                ["后端功能回归", "107 项测试全部通过", "2026-08-03 本机执行 pytest"],
                ["前端交付性", "生产构建成功", "2026-06-30 本机执行 npm run build"],
                ["接口组织规模", "58 条路由、7 个主要 API 模块方向", "backend/app/api 代码统计"],
                ["服务层体量", "26 个服务模块", "backend/app/services 目录统计"],
                ["持续验证能力", "仓库包含 ci.yml 工作流", ".github/workflows/ci.yml"],
            ],
        ),
        [3.6, 4.6, 6.8],
    )
    add_table_block(
        doc,
        TableItem(
            "表A-4",
            "异常场景处理与回退策略表",
            ["异常场景", "系统处理方式", "对比赛稳定性的意义"],
            [
                ["正文提取不足", "降低 parse_quality 并输出解析告警", "避免误导性高分"],
                ["扫描件或图片版 PDF", "尝试 OCR 兜底，失败则提示重传标准文件", "保留可解释边界"],
                ["ZIP 包含异常文件", "过滤或跳过异常文件，保留可处理样本", "避免一份坏文件拖垮整包"],
                ["AI 服务不可用", "切换为 offline_fallback", "保证主流程仍可演示"],
                ["批量任务过多", "根据数量选择更稳的规则主链", "优先保障速度与可完成性"],
            ],
        ),
        [3.4, 5.0, 6.6],
    )
    add_body_paragraph(doc, "需要特别说明的是，本稿中的工程验证口径全部采用绝对时间和可回溯来源表达，例如“2026年8月3日本机执行”“仓库当前包含的 ci.yml 工作流”等，而不使用含糊的“已支持”“已有较完善测试”表述。这样做的目的是让评审在阅读时可以明确区分：哪些是公开政策背景，哪些是当前仓库事实，哪些是当日实测结果。", first_line=True)
    _figure(
        doc,
        FigureItem("图A-1", "测试验证支撑结构图", "展示自动化测试、前端构建、CI 与部署检查之间的支撑关系。"),
    )
    add_figure_note(doc, "附录中的该图用于概括验证材料结构，使评委在进入多张明细表之前先看见总体关系。")
    _figure(
        doc,
        FigureItem("图A-2", "CI 流程示意图", "GitHub Actions 包含后端 pytest 与前端构建两个主要流程。"),
    )
    add_figure_note(doc, "该图与仓库当前的 ci.yml 一一对应，目的是证明平台不仅能在本机跑通，也具备基础的持续验证能力。")
    doc.add_page_break()


def appendix_b(doc: Document) -> None:
    add_section_heading(doc, 1, "附录B 部署运行与接口清单")
    add_body_paragraph(doc, "本项目支持本地开发运行与Docker Compose演示部署两种主要方式。比赛或展示环境可直接使用Docker Compose启动前端、后端、MySQL、Redis与Celery Worker；本地环境则可通过批处理脚本分别启动前后端服务。", first_line=True)
    add_body_paragraph(doc, "部署材料在本参赛稿中只保留证明性信息，不展开成长篇使用手册。其作用是说明系统已经考虑到浏览器访问、后端健康检查、数据库、任务队列、报告目录和静态资源发布等现实运行要素，评委无需推测“这套系统能不能真的被跑起来”。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表B-1",
            "部署检查清单",
            ["检查项", "说明"],
            [
                ["前端访问", "默认 http://127.0.0.1:5173 或 localhost:5173"],
                ["后端健康检查", "GET /api/health"],
                ["数据库连接", "MySQL 8，支持本地与 Docker 两种方式"],
                ["异步任务", "Docker 模式下默认启用 Redis + Celery"],
                ["报告目录", "data/reports/"],
            ],
        ),
        [5.2, 10.3],
    )
    add_table_block(
        doc,
        TableItem(
            "表B-1-产",
            "关键运行目录与产物说明",
            ["目录/对象", "说明"],
            [
                ["data/uploads/", "原始上传简历文件存放目录"],
                ["data/extracted/", "ZIP 解压后的临时文件目录"],
                ["data/reports/", "Word/PDF 报告输出目录"],
                ["frontend/dist/", "前端构建产物目录"],
                ["docker-compose.yml", "比赛演示与部署启动入口"],
            ],
        ),
        [5.6, 9.8],
    )
    add_table_block(
        doc,
        TableItem(
            "表B-1-扩",
            "API 模块与路由规模概览",
            ["模块文件", "职责方向", "路由数"],
            get_route_overview_rows(),
        ),
        [4.4, 6.0, 3.0],
    )
    add_table_block(
        doc,
        TableItem(
            "表B-2",
            "关键接口清单",
            ["接口", "所属方向", "作用"],
            get_key_endpoint_rows(),
        ),
        [6.2, 3.4, 5.8],
    )
    add_table_block(
        doc,
        TableItem(
            "表B-3",
            "接口分层与展示用途说明",
            ["接口层级", "代表接口", "在比赛展示中的作用"],
            [
                ["分析主链接口", "POST /resumes/analyze", "展示核心闭环能力"],
                ["批量任务接口", "POST /resumes/analyze-zip", "展示平台处理多份样本的稳定性"],
                ["历史与报告接口", "GET /history/{record_id}、GET /reports/{report_id}/download", "展示结果沉淀与材料化输出"],
                ["教师端接口", "GET /teacher/stats", "展示群体诊断能力"],
                ["管理端接口", "GET /admin/users、POST /admin/storage/cleanup", "展示治理与维护能力"],
            ],
        ),
        [3.6, 4.6, 6.8],
    )
    add_table_block(
        doc,
        TableItem(
            "表B-4",
            "完整接口清单（上）",
            ["接口", "所属方向", "作用"],
            get_all_endpoint_rows_split()[0],
        ),
        [5.8, 3.2, 6.4],
    )
    add_table_block(
        doc,
        TableItem(
            "表B-5",
            "完整接口清单（下）",
            ["接口", "所属方向", "作用"],
            get_all_endpoint_rows_split()[1],
        ),
        [5.8, 3.2, 6.4],
    )
    add_body_paragraph(doc, "从接口组织方式上也可以看出项目的平台化特征。分析主链、教师端、管理端和工作台相关能力并没有混杂在同一个路由文件中，而是按角色和业务边界拆分到不同模块。这样的组织方式既有利于后续维护，也更适合作为比赛作品向评委证明“系统已经形成了清晰的工程结构”。", first_line=True)
    doc.add_page_break()


def appendix_c(doc: Document) -> None:
    add_section_heading(doc, 1, "附录C 数据安全、治理与运行边界说明")
    add_body_paragraph(doc, "平台默认采用本地私有存储策略，上传文件、解压文件和报告文件分别存放于 data/uploads、data/extracted 和 data/reports 目录。登录用户按 user_id 隔离，游客按 guest_session_id 隔离，教师端默认查看统计元数据，不直接暴露简历正文。", first_line=True)
    add_body_paragraph(doc, "在AI增强方面，只有在配置了 DEEPSEEK_API_KEY 且用户开启相关选项时，平台才会把简历文本与规则评分发送至外部API；如网络不可用、配置缺失或接口异常，系统会自动回退到本地规则分析并标记为 offline_fallback。删除历史记录时，平台会同步清理原始简历、解压临时文件和报告文件，以控制运行期文件生命周期。", first_line=True)
    add_body_paragraph(doc, "这一附录的重点不是泛泛而谈“我们重视安全”，而是把当前系统已经落实的边界明确写清：哪些数据默认在本地、哪些场景才会触发外部调用、不同角色能看见什么、删除动作会联动清理哪些文件。对于高校场景和比赛场景来说，这种明确边界比抽象口号更重要，也更容易被评委认可。", first_line=True)
    add_table_block(
        doc,
        TableItem(
            "表C-1",
            "数据安全与治理措施表",
            ["措施", "说明"],
            [
                ["本地存储隔离", "上传、解压、报告文件分目录管理"],
                ["用户维度隔离", "登录用户与游客记录分离"],
                ["AI 调用开关", "可完全关闭外部 AI 调用，保留离线运行能力"],
                ["删除联动清理", "删除记录时同步清理相关文件"],
                ["ZIP 安全控制", "拒绝路径穿越并限制解压总量"],
            ],
        ),
        [5.2, 10.3],
    )
    add_table_block(
        doc,
        TableItem(
            "表C-2",
            "数据生命周期链路说明",
            ["阶段", "处理说明"],
            [
                ["上传阶段", "文件进入 uploads 目录并完成格式、大小与ZIP安全校验"],
                ["解析阶段", "从原始文件提取正文、板块、实体和告警信息"],
                ["产物阶段", "生成评分、匹配结果、建议与报告文件"],
                ["查看阶段", "学生查看本人结果，教师查看群体统计元数据"],
                ["删除阶段", "删除记录时同步清理原始文件、解压文件和报告文件"],
            ],
        ),
        [4.4, 11.0],
    )
    add_table_block(
        doc,
        TableItem(
            "表C-3",
            "角色权限与可见范围说明",
            ["角色", "主要可见内容", "限制边界"],
            [
                ["学生", "本人分析结果、报告、任务状态、历史记录", "默认仅访问本人数据"],
                ["教师", "班级/专业/年级统计与学生记录元数据", "默认不直接查看学生简历正文"],
                ["管理员", "用户、配置、审计日志、清理能力", "负责治理，不参与具体求职分析输出"],
                ["游客", "当前浏览器会话中的匿名分析记录", "通过 guest_session_id 隔离，登录后可导入"],
            ],
        ),
        [2.8, 6.0, 6.6],
    )
    add_table_block(
        doc,
        TableItem(
            "表C-4",
            "运行模式与开关说明",
            ["运行模式/开关", "作用说明"],
            [
                ["enable_ai", "控制是否尝试外部 AI 增强"],
                ["offline_fallback", "AI 不可用时回退到本地规则主链"],
                ["USE_CELERY", "控制是否启用异步任务队列"],
                ["guest_session_id", "用于游客模式记录隔离"],
                ["report download on demand", "PDF 报告按需生成，降低主流程等待时间"],
            ],
        ),
        [5.0, 10.5],
    )
    add_body_paragraph(doc, "从运行边界看，项目最重要的策略是把“是否启用增强能力”和“主链是否能够完成”彻底分开。这样既保留了更强表达能力的空间，也保证在比赛现场、弱网络或配置不完整场景下，平台仍然可以稳定完成上传、解析、评价、匹配和报告输出。", first_line=True)
    add_body_paragraph(doc, "因此，本项目在能力表达上始终保持一个基本原则：凡是必须依赖外部服务、复杂环境或额外数据源的能力，都不写成“主链刚需”；凡是已经能在仓库中被运行、被测试、被部署说明支撑的能力，才在文稿中作为当前实现写入。这样的写法既保证了时效性和真实性，也使参赛文档更接近正式技术项目书应有的可信风格。", first_line=True)


def build_document() -> None:
    global FIGURE_PATHS
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_PATHS = ensure_figure_assets(ASSET_DIR, FONT_PATH)
    doc = Document()
    configure_document(doc)

    figures = [
        FigureItem("图1-1", "三角色协同关系图", ""),
        FigureItem("图1-2", "平台应用效果路径图", ""),
        FigureItem("图1-3", "科研支撑到系统实现的映射图", ""),
        FigureItem("图2-1", "系统总体架构图", ""),
        FigureItem("图2-2", "核心业务流程图", ""),
        FigureItem("图3-1", "六维评价模型图", ""),
        FigureItem("图3-2", "比赛演示流程图", ""),
        FigureItem("图3-3", "数据流与安全边界图", ""),
        FigureItem("图3-4", "任务处理流程图", ""),
        FigureItem("图3-5", "项目可信性来源结构图", ""),
        FigureItem("图4-1", "平台应用效果路径图", ""),
        FigureItem("图4-2", "比赛展示流程图", ""),
        FigureItem("图5-1", "当前能力与未来扩展路线图", ""),
        FigureItem("图5-2", "项目可信性来源结构图", ""),
        FigureItem("图A-1", "测试验证支撑结构图", ""),
        FigureItem("图A-2", "CI 流程示意图", ""),
    ]
    tables = [
        TableItem("表H-1", "项目核心亮点总览", [], []),
        TableItem("表1-1", "赛题关注问题与项目对应切入点", [], []),
        TableItem("表1-2", "同类方案与本项目差异对比", [], []),
        TableItem("表1-3", "项目主要工作与创新归纳", [], []),
        TableItem("表2-1", "问题界定与解决思路对应表", [], []),
        TableItem("表2-2", "功能模块总览", [], []),
        TableItem("表2-3", "输入输出与角色边界", [], []),
        TableItem("表2-4", "赛题要求与系统实现对照", [], []),
        TableItem("表3-1", "文件类型支持与处理方式", [], []),
        TableItem("表3-2", "结构化识别的核心字段体系", [], []),
        TableItem("表3-3", "六维评价维度及依据", [], []),
        TableItem("表3-4", "岗位匹配结果输出字段", [], []),
        TableItem("表3-5", "技术选型与作用", [], []),
        TableItem("表3-5-扩", "后端服务模块与职责摘要", [], []),
        TableItem("表3-5-续", "后端服务模块与职责摘要（续）", [], []),
        TableItem("表3-6", "测试与构建现状归纳", [], []),
        TableItem("表3-7", "分析结果关键字段样例", [], []),
        TableItem("表3-8", "案例链路分阶段输出示意", [], []),
        TableItem("表3-9", "结果页关键信息块与展示作用", [], []),
        TableItem("表3-10", "报告内容组成与使用对象", [], []),
        TableItem("表3-11", "稳定性策略与对应机制", [], []),
        TableItem("表4-1", "不同用户对象收益表", [], []),
        TableItem("表4-2", "推广应用场景表", [], []),
        TableItem("表4-3", "比赛评审关注点与项目响应关系表", [], []),
        TableItem("表5-1", "当前局限性与改进方向对照", [], []),
        TableItem("表5-2", "后续实施路径建议表", [], []),
        TableItem("表A-1", "测试文件与用例统计表", [], []),
        TableItem("表A-1-扩", "测试文件覆盖明细", [], []),
        TableItem("表A-1-类", "测试类别统计", [], []),
        TableItem("表A-2", "测试与构建结论汇总", [], []),
        TableItem("表A-3", "验证口径与材料来源对应表", [], []),
        TableItem("表A-4", "异常场景处理与回退策略表", [], []),
        TableItem("表B-1", "部署检查清单", [], []),
        TableItem("表B-1-产", "关键运行目录与产物说明", [], []),
        TableItem("表B-1-扩", "API 模块与路由规模概览", [], []),
        TableItem("表B-2", "关键接口清单", [], []),
        TableItem("表B-3", "接口分层与展示用途说明", [], []),
        TableItem("表B-4", "完整接口清单（上）", [], []),
        TableItem("表B-5", "完整接口清单（下）", [], []),
        TableItem("表C-1", "数据安全与治理措施表", [], []),
        TableItem("表C-2", "数据生命周期链路说明", [], []),
        TableItem("表C-3", "角色权限与可见范围说明", [], []),
        TableItem("表C-4", "运行模式与开关说明", [], []),
    ]

    add_cover(doc)
    build_summary(doc)
    add_toc_placeholder(doc)
    build_figure_list(doc, figures)
    build_table_list(doc, tables)
    chapter_one(doc)
    chapter_two(doc)
    chapter_three(doc)
    chapter_four(doc)
    chapter_five(doc)
    references(doc)
    appendix_a(doc)
    appendix_b(doc)
    appendix_c(doc)
    doc.save(DOCX_PATH)


if __name__ == "__main__":
    build_document()
