import re
from pathlib import Path
from typing import Any


SECTION_KEYS = [
    "basic_info",
    "education",
    "internship",
    "projects",
    "campus",
    "skills",
    "awards",
    "summary",
]

SECTION_PATTERNS = {
    "basic_info": [
        "个人信息",
        "基本信息",
        "联系方式",
        "联系信息",
        "个人资料",
        "基本资料",
    ],
    "education": [
        "教育背景",
        "教育经历",
        "教育信息",
        "学习经历",
        "学历背景",
        "学习背景",
        "主修课程",
        "所学课程",
        "专业课程",
    ],
    "internship": [
        "实习经历",
        "工作经历",
        "工作经验",
        "实践经历",
        "社会实践",
        "校外实践",
        "任职经历",
        "职业经历",
    ],
    "projects": [
        "项目经历",
        "项目经验",
        "项目/实训经历",
        "项目实训经历",
        "实训经历",
        "科研经历",
        "课程项目",
        "项目实践",
        "项目一",
        "项目二",
        "项目三",
    ],
    "campus": [
        "校园经历",
        "校园实践",
        "校内实践",
        "社团经历",
        "学生工作",
        "在校经历",
        "学生干部",
    ],
    "skills": [
        "专业技能",
        "技能证书",
        "技能特长",
        "个人技能",
        "技术技能",
        "核心技能",
        "语言能力",
        "软件技能",
        "办公技能",
        "证书技能",
    ],
    "awards": [
        "获奖经历",
        "荣誉证书",
        "荣誉奖项",
        "获奖情况",
        "奖项证书",
        "奖学金",
    ],
    "summary": [
        "自我评价",
        "个人总结",
        "个人优势",
        "求职意向",
        "目标岗位",
        "意向岗位",
        "应聘岗位",
        "期望岗位",
        "求职方向",
    ],
}

TARGET_POSITION_PATTERNS = [
    r"(?:求职意向|意向岗位|目标岗位|应聘岗位|应聘职位|期望岗位|期望职位|求职方向)\s*[:：]\s*(.+)",
    r"(?:求职意向|意向岗位|目标岗位|应聘岗位|应聘职位|期望岗位|期望职位|求职方向)\s+(.+)",
]

DATE_RANGE_RE = re.compile(
    r"(?:20\d{2}|19\d{2})[./年-]?\s*(?:0?[1-9]|1[0-2])?\s*(?:-|至|~|—|–|到)\s*(?:20\d{2}|19\d{2}|今|现在|至今|present)",
    re.IGNORECASE,
)
SCHOOL_RE = re.compile(r"(大学|学院|学校|本科|专科|大专|硕士|研究生|博士|专业|主修|课程)")
ORG_RE = re.compile(r"(公司|集团|工作室|中心|传媒|科技|网络|岗位|职位|实习|助理|运营|编辑|剪辑|销售|客服|教师)")
PROJECT_RE = re.compile(r"(项目|实训|课题|系统|平台|小程序|网站|账号|视频号|公众号|社群|活动策划|作品|案例)")
SKILL_RE = re.compile(r"(技能|证书|熟练|掌握|了解|英语|普通话|Office|Excel|Word|PPT|Python|SQL|Vue|React|剪映|PS|PR|AE|Photoshop)", re.IGNORECASE)
CONTACT_RE = re.compile(r"(@|邮箱|电话|手机|微信|QQ|1[3-9]\d{9})", re.IGNORECASE)


def parse_resume(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    warnings: list[str] = []
    if path.name.startswith("~$"):
        raise ValueError("Word 临时文件已跳过，请上传正式简历文件")
    if suffix == ".docx":
        text = _parse_docx(path)
    elif suffix == ".pdf":
        text, warnings = _parse_pdf(path)
    else:
        raise ValueError(f"不支持的文件类型：{suffix}")
    sections = detect_sections(text)
    keywords = extract_keywords(text)
    detected_target_position = detect_target_position(text, sections)
    parse_quality, parse_warnings = evaluate_parse_quality(text, sections, warnings, suffix)
    return {
        "raw_text": text,
        "sections": sections,
        "detected_keywords": keywords,
        "detected_target_position": detected_target_position,
        "warnings": warnings,
        "parse_quality": parse_quality,
        "parse_warnings": parse_warnings,
    }


def _parse_docx(path: Path) -> str:
    from docx import Document

    doc = Document(path)
    chunks: list[str] = []
    seen: set[str] = set()

    def add_text(value: str) -> None:
        text = _normalize_line(value)
        if text and text not in seen:
            chunks.append(text)
            seen.add(text)

    def add_paragraphs(paragraphs: Any) -> None:
        for paragraph in paragraphs:
            add_text(paragraph.text)

    def add_table(table: Any) -> None:
        for row in table.rows:
            row_cells: list[str] = []
            for cell in row.cells:
                cell_parts = [_normalize_line(paragraph.text) for paragraph in cell.paragraphs]
                cell_text = " ".join(part for part in cell_parts if part)
                if cell_text:
                    row_cells.append(cell_text)
                for nested_table in cell.tables:
                    add_table(nested_table)
            if row_cells:
                add_text(" | ".join(row_cells))

    add_paragraphs(doc.paragraphs)
    for table in doc.tables:
        add_table(table)
    for section in doc.sections:
        add_paragraphs(section.header.paragraphs)
        add_paragraphs(section.footer.paragraphs)
        for table in section.header.tables:
            add_table(table)
        for table in section.footer.tables:
            add_table(table)

    # Text boxes, shapes and some WPS templates store visible text in raw Word XML nodes.
    for element in doc.part.element.iter():
        if element.tag.endswith("}t") and element.text:
            add_text(element.text)

    return "\n".join(chunks)


def _parse_pdf(path: Path) -> tuple[str, list[str]]:
    import pdfplumber

    warnings: list[str] = []
    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text.strip())
    text = "\n".join(chunks)
    if len(text.strip()) >= 30:
        return text, warnings
    warnings.append("PDF 文本较少，可能是扫描版或图片版简历。")
    ocr_text = _ocr_pdf(path)
    if ocr_text.strip():
        warnings.append("已尝试 OCR 兜底提取文本。")
        return ocr_text, warnings
    warnings.append("OCR 未能提取有效文本，请检查文件是否为清晰扫描件。")
    return text, warnings


def _ocr_pdf(path: Path) -> str:
    try:
        import numpy as np
        import pdfplumber
        from paddleocr import PaddleOCR
    except Exception:
        return ""

    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    chunks: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                image = page.to_image(resolution=160).original
                result = ocr.ocr(np.array(image), cls=True)
                for page_result in result or []:
                    for line in page_result or []:
                        if len(line) >= 2 and line[1]:
                            chunks.append(str(line[1][0]))
    except Exception:
        return ""
    return "\n".join(chunks)


def detect_sections(text: str) -> dict[str, list[str]]:
    lines = [_normalize_line(line) for line in text.splitlines()]
    sections = {key: [] for key in SECTION_KEYS}
    current = "summary"

    for line in [line for line in lines if line]:
        heading = _detect_heading_section(line)
        if heading:
            current = heading
            sections[current].append(line)
            continue

        inferred = _infer_content_section(line, current)
        if inferred and _should_switch_section(line, current, inferred):
            current = inferred
        target = inferred or current
        sections[target].append(line)

    return _dedupe_sections(sections)


def extract_keywords(text: str, limit: int = 30) -> list[str]:
    try:
        import jieba
    except Exception:
        words = re.findall(r"[\u4e00-\u9fa5A-Za-z0-9+#.]{2,}", text)
    else:
        words = [word.strip() for word in jieba.cut(text)]
    stopwords = {"本人", "负责", "参与", "具有", "以及", "进行", "通过", "相关", "简历", "工作", "项目"}
    counts: dict[str, int] = {}
    for word in words:
        if len(word) < 2 or word in stopwords:
            continue
        if re.fullmatch(r"\d+", word):
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]]


def detect_target_position(text: str, sections: dict[str, list[str]]) -> str:
    candidates = list(sections.get("summary", []))
    candidates.extend(line.strip() for line in text.splitlines() if line.strip())
    for line in candidates:
        for pattern in TARGET_POSITION_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if not match:
                continue
            cleaned = _clean_target_position(match.group(1))
            if cleaned:
                return cleaned
    return ""


def evaluate_parse_quality(
    text: str,
    sections: dict[str, list[str]],
    parser_warnings: list[str],
    suffix: str,
) -> tuple[str, list[str]]:
    stripped = text.strip()
    core_keys = ["basic_info", "education", "internship", "projects", "skills"]
    core_present = sum(1 for key in core_keys if sections.get(key))
    warnings = list(dict.fromkeys(parser_warnings))

    if not stripped:
        warnings.append("未能从文件中提取到正文，可能是图片版简历、文本框版式或文件损坏。")
    elif len(stripped) < 120:
        warnings.append("提取到的正文较短，评分仅供参考。")
    if core_present <= 1:
        warnings.append("核心模块识别不足，可能存在特殊排版或图片化内容。")
    elif core_present <= 2:
        warnings.append("部分核心模块识别不足，建议核对解析结果。")
    if suffix == ".docx" and len(stripped) < 80:
        warnings.append("DOCX 可能使用了特殊模板、文本框或图片内容，建议另存为标准 DOCX/PDF 后重试。")

    if not stripped or len(stripped) < 80 or core_present <= 1:
        return "low", warnings
    if len(stripped) < 300 or core_present <= 2 or warnings:
        return "medium", warnings
    return "high", warnings


def _detect_heading_section(line: str) -> str:
    clean = _normalize_heading(line)
    for key, aliases in SECTION_PATTERNS.items():
        for alias in aliases:
            if alias.lower() in clean.lower():
                if len(clean) <= 32 or _looks_like_heading(line) or alias in {"项目一", "项目二", "项目三"}:
                    return key
    return ""


def _infer_content_section(line: str, current: str) -> str:
    if CONTACT_RE.search(line):
        return "basic_info"
    if SKILL_RE.search(line) and current not in {"projects", "internship"}:
        return "skills"
    if PROJECT_RE.search(line):
        return "projects"
    if DATE_RANGE_RE.search(line) and ORG_RE.search(line):
        return "internship"
    if SCHOOL_RE.search(line) and current not in {"skills", "projects", "internship"}:
        return "education"
    if re.search(r"(学生会|社团|班委|团委|志愿者|校园)", line):
        return "campus"
    return ""


def _should_switch_section(line: str, current: str, inferred: str) -> bool:
    if inferred == current:
        return False
    if _looks_like_heading(line):
        return True
    if inferred in {"projects", "internship"} and (DATE_RANGE_RE.search(line) or PROJECT_RE.search(line)):
        return True
    if current == "summary" and inferred in {"basic_info", "education", "skills"}:
        return True
    return False


def _looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if re.match(r"^[一二三四五六七八九十]+[、.．]", stripped):
        return True
    if re.match(r"^[（(]?[0-9一二三四五六七八九十]+[）).、．]", stripped):
        return True
    if re.search(r"[:：]$", stripped):
        return True
    return len(stripped) <= 18 and not DATE_RANGE_RE.search(stripped)


def _normalize_heading(line: str) -> str:
    clean = _normalize_line(line)
    clean = re.sub(r"^[（(]?[0-9一二三四五六七八九十]+[）).、．]\s*", "", clean)
    clean = clean.strip("：:|-_ ")
    return clean


def _normalize_line(value: str) -> str:
    value = value.replace("\u3000", " ").replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _dedupe_sections(sections: dict[str, list[str]]) -> dict[str, list[str]]:
    cleaned: dict[str, list[str]] = {}
    for key, lines in sections.items():
        seen: set[str] = set()
        cleaned[key] = []
        for line in lines:
            if line not in seen:
                cleaned[key].append(line)
                seen.add(line)
    return cleaned


def _clean_target_position(value: str) -> str:
    cleaned = re.split(r"(?:期望城市|工作地点|薪资要求|到岗时间|实习时间|求职类型)", value, maxsplit=1)[0]
    cleaned = cleaned.replace("|", "/")
    cleaned = re.sub(r"[（(].*?[)）]", "", cleaned)
    parts = [part.strip(" ：:;；，,、。 \t") for part in re.split(r"[/、，,；;|]+", cleaned) if part.strip(" ：:;；，,、。 \t")]
    normalized: list[str] = []
    for part in parts:
        if len(part) < 2:
            continue
        if re.fullmatch(r"(本科|硕士|大专|全职|实习|兼职|在校生|应届生)", part):
            continue
        normalized.append(part)
    unique_parts = list(dict.fromkeys(normalized))
    return " / ".join(unique_parts[:3]) if unique_parts else ""
