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
        "求职意向",
        "目标岗位",
        "意向岗位",
        "应聘岗位",
        "期望岗位",
        "求职方向",
        "职业目标",
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
        "实习",
        "工作",
        "实习经历",
        "工作经历",
        "工作经验",
        "就业经历",
        "工作实践",
        "岗位实践",
        "实践经历",
        "社会实践",
        "校外实践",
        "任职经历",
        "职业经历",
        "工作/实习经历",
        "实习/工作经历",
        "工作实习经历",
        "实习与工作",
    ],
    "projects": [
        "项目经历",
        "项目经验",
        "项目作品",
        "作品经历",
        "项目/实训经历",
        "项目实训经历",
        "实训项目",
        "实训经历",
        "科研经历",
        "课程项目",
        "课程设计",
        "项目实践",
        "个人作品",
        "设计作品",
        "作品集",
        "作品展示",
        "项目一",
        "项目二",
        "项目三",
    ],
    "campus": [
        "校园经历",
        "校园实践",
        "校内外经历",
        "校内外实践",
        "校内实践",
        "社团经历",
        "社会活动",
        "志愿经历",
        "学生工作",
        "在校经历",
        "学生干部",
    ],
    "skills": [
        "专业技能",
        "职业技能",
        "技能",
        "技能清单",
        "技能证书",
        "技能特长",
        "技能专长",
        "个人技能",
        "技术技能",
        "计算机技能",
        "核心技能",
        "语言能力",
        "软件技能",
        "办公技能",
        "办公软件",
        "设计软件",
        "证书技能",
        "掌握软件",
        "软件掌握",
        "工具技能",
    ],
    "awards": [
        "个人荣誉",
        "所获荣誉",
        "荣誉",
        "证书",
        "获奖经历",
        "荣誉证书",
        "荣誉奖项",
        "获奖情况",
        "奖项证书",
        "获奖证书",
        "奖学金",
        "证书与荣誉",
        "证书荣誉",
        "资格证书",
        "资质证书",
    ],
    "summary": [
        "自我评价",
        "自我介绍",
        "个人总结",
        "个人评价",
        "个人优势",
        "个人简介",
        "性格特点",
        "简介",
        "关于我",
    ],
}

# 英文 / 混排标题（设计、传媒类简历常见）
SECTION_PATTERNS_EN: dict[str, list[str]] = {
    "basic_info": ["personal information", "contact", "profile"],
    "education": ["education", "education background"],
    "internship": ["work experience", "experience", "employment", "internship"],
    "projects": ["projects", "project experience", "portfolio"],
    "campus": ["campus", "activities"],
    "skills": ["skills", "technical skills", "certificates"],
    "awards": ["awards", "honors", "certifications"],
    "summary": ["summary", "objective", "about me"],
}


NAME_LABEL_RE = re.compile(r"(?:姓名|名字|name)\s*[:：]\s*([^\s|，,;；]{2,8})", re.I)
RESUME_NOISE_WORDS = frozenset(
    {"简历", "求职", "个人", "基本信息", "个人信息", "联系方式", "电话", "邮箱", "手机", "微信"}
)

TARGET_POSITION_PATTERNS = [
    r"(?:求职意向|意向岗位|目标岗位|应聘岗位|应聘职位|期望岗位|期望职位|求职方向)\s*[:：]\s*(.+)",
    r"(?:求职意向|意向岗位|目标岗位|应聘岗位|应聘职位|期望岗位|期望职位|求职方向)\s+(.+)",
]

DATE_RANGE_RE = re.compile(
    r"(?:20\d{2}|19\d{2}|20xx|19xx)[./年-]?\s*(?:0?[1-9]|1[0-2])?\s*(?:-|至|~|—|–|到)\s*(?:20\d{2}|19\d{2}|20xx|19xx|今|现在|至今|present)",
    re.IGNORECASE,
)
SCHOOL_RE = re.compile(r"(大学|学院|学校|本科|专科|大专|硕士|研究生|博士|专业|主修|课程)")
ORG_RE = re.compile(
    r"(公司|集团|工作室|中心|传媒|科技|网络公司|岗位|职位|实习|助理|运营|销售|客服|教师|"
    r"影视公司|广告公司|传播公司|文化公司|设计助理|设计师|有限公司|股份公司)"
)
PROJECT_RE = re.compile(
    r"(项目|实训|课题|系统|平台|小程序|网站|账号|视频号|公众号|社群|作品|案例|"
    r"短片|海报|片头|包装|拍摄|账号运营|毕业设计)"
)
SKILL_RE = re.compile(
    r"(技能|证书|熟练|掌握|了解|英语|普通话|Office|Excel|Word|PPT|WPS|Python|SQL|Vue|React|"
    r"剪映|Canva|秀米|Photoshop|Premiere|HarmonyOS|办公软件|办公自动化|设计剪辑|"
    r"(?<![A-Za-z])(?:PS|PR|AE)(?![A-Za-z]))",
    re.IGNORECASE,
)
AWARD_RE = re.compile(r"(获奖|荣誉|奖学金|Uskills|优秀学生|一等奖|二等奖|三等奖|竞赛获奖|提名|大赛)", re.IGNORECASE)
AWARD_CONTEXT_RE = re.compile(r"(个人荣誉|荣誉证书|证书荣誉|获奖情况|获奖证书)", re.IGNORECASE)
CERTIFICATE_ONLY_RE = re.compile(r"(证书|资格证|等级证|英语四级|英语六级|普通话|初级|中级|高级)", re.IGNORECASE)
SUMMARY_HEADING_RE = re.compile(
    r"(自我评价|个人评价|自我介绍|个人总结|性格特点|个人优势|个人简介|关于我)",
    re.IGNORECASE,
)
SUMMARY_SOFT_RE = re.compile(
    r"(为人|性格|沟通|协调|团队协作|学习能力|学习力|执行力|抗压|适应|乐观|踏实|"
    r"责任心|团队意识|共情|细心|严谨|亲和|积极主动|吃苦耐劳)",
    re.IGNORECASE,
)
SUMMARY_PROSE_START_RE = re.compile(
    r"^(?:[-–—•·\s]*)(?:本人|具备|热爱|擅长|性格|为人|做事|工作严谨|拥有|秉持|期待|希望以)",
    re.IGNORECASE,
)
ACTION_RE = re.compile(r"(负责|参与|协助|配合|完成|执行|制作|处理|运营|维护|撰写|剪辑|设计|拍摄|策划|发布|管理|优化)")
CAMPUS_ORG_RE = re.compile(r"(学生会|社团|班委|团委|志愿者|干部|干事|部长|主席|协会|实验室助手)")
CAMPUS_CONTEXT_RE = re.compile(r"(校园|学校|大学期间|在校期间|校内|校外实践|社会实践)")
PROJECT_PRODUCT_RE = re.compile(r"(小程序|平台|系统|网站|毕业设计|课题|实训|项目|App|APP|数据分析)")
INLINE_HEADING_MARKERS = [
    "个人信息",
    "基本信息",
    "联系方式",
    "求职意向",
    "目标岗位",
    "教育背景",
    "教育经历",
    "实习经历",
    "工作经历",
    "实习",
    "工作",
    "项目经历",
    "项目经验",
    "项目作品",
    "校园经历",
    "校内外经历",
    "社会实践",
    "专业技能",
    "职业技能",
    "办公软件",
    "设计剪辑",
    "个人荣誉",
    "荣誉证书",
    "证书荣誉",
    "获奖情况",
    "自我评价",
    "个人评价",
]
CONTACT_RE = re.compile(r"(@|邮箱|电话|手机|联系方式|微信|Wechat|QQ|现居|现居地|居住地|所在地|期望薪资|薪资|1[3-9]\d{9})", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+86[- ]?)?1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}(?!\d)")
WECHAT_RE = re.compile(r"(?:微信|Wechat|WeChat)\s*[:：]?\s*([A-Za-z0-9_-]{3,30})", re.IGNORECASE)
QQ_RE = re.compile(r"(?:QQ|qq)\s*[:：]?\s*([1-9]\d{4,11})")
SALARY_RE = re.compile(r"(?:期望薪资|薪资|薪酬)\s*[:：]?\s*([0-9kK千万元+\-~—至到/]+(?:/月|每月|月)?|面议)")
LOCATION_RE = re.compile(r"(?:现居|现居地|居住地|所在地|地址)\s*[:：]?\s*([\u4e00-\u9fa5A-Za-z]{2,20})")
# 中文姓名多为 2–4 字；勿扩到 6，否则会把「人力资源管理」等专业名误判为人名
NAME_HINT_RE = re.compile(r"^[\u4e00-\u9fa5·]{2,4}$")
MAJOR_HINT_RE = re.compile(
    r"(管理|工程|科学|技术|经济|法学|医学|文学|理学|工学|农学|艺术|资源|人力|会计|金融|"
    r"计算机|软件|电子|机械|土木|新闻|广告|设计|英语|日语|数学|物理|化学|生物|护理|"
    r"教育|师范|营销|贸易|物流|心理|统计|通信|自动化|建筑|环境|材料|食品|药学|临床|"
    r"政治|历史|哲学|社会|公共|商务|国际|信息|网络|数据|智能|媒体|传播|编辑|财务|"
    r"本科|硕士|博士|专科|大专|学士|研究生|主修|专业)"
)
LABEL_VALUE_FIELDS = frozenset(
    {
        "姓名",
        "求职意向",
        "意向岗位",
        "目标岗位",
        "应聘岗位",
        "应聘职位",
        "期望岗位",
        "期望职位",
        "求职方向",
        "电话",
        "手机",
        "联系方式",
        "邮箱",
        "微信",
        "wechat",
        "qq",
        "现居",
        "现居地",
        "居住地",
        "所在地",
        "期望薪资",
        "薪资",
        "年龄",
        "学历",
        "政治面貌",
        "民族",
        "籍贯",
        "身高",
        "体重",
    }
)

TECH_SKILL_PATTERNS = [
    r"Python(?:\s*3)?",
    r"Java(?:Script|)?",
    r"TypeScript",
    r"C\+\+",
    r"C#",
    r"\bGo\b",
    r"\bRust\b",
    r"Vue(?:\.js|3)?",
    r"React(?:\.js)?",
    r"Node(?:\.js)?",
    r"Spring(?:Boot)?",
    r"MySQL",
    r"PostgreSQL",
    r"Redis",
    r"MongoDB",
    r"Docker",
    r"Kubernetes",
    r"\bK8s\b",
    r"Linux",
    r"\bGit\b",
    r"\bSQL\b",
    r"Excel",
    r"PowerPoint",
    r"\bPPT\b",
    r"Photoshop",
    r"Premiere",
    r"剪映",
    r"数据分析",
    r"机器学习",
    r"深度学习",
    r"TensorFlow",
    r"PyTorch",
    r"Tableau",
    r"Power\s*BI",
    r"Axure",
    r"Figma",
    r"UI设计",
    r"UX设计",
    r"产品经理",
    r"新媒体运营",
    r"社群运营",
    r"用户增长",
    r"内容运营",
    r"视频剪辑",
    r"平面设计",
]


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
    if not detected_target_position:
        detected_target_position = detect_target_from_filename(path.stem)
    parse_quality, parse_warnings = evaluate_parse_quality(text, sections, warnings, suffix)
    name_hint = extract_name_hint(sections, text)
    return {
        "raw_text": text,
        "sections": sections,
        "detected_keywords": keywords,
        "detected_target_position": detected_target_position,
        "contact_entities": extract_contact_entities(text),
        "name_hint": name_hint,
        "warnings": warnings,
        "parse_quality": parse_quality,
        "parse_warnings": parse_warnings,
        "layout_complexity": estimate_layout_complexity(text),
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

    body_text = "\n".join(chunks)
    xml_chunks: list[str] = []
    xml_seen: set[str] = set()
    for element in doc.part.element.iter():
        if element.tag.endswith("}t") and element.text:
            text = _normalize_line(element.text)
            if text and text not in xml_seen:
                xml_chunks.append(text)
                xml_seen.add(text)

    # 很多求职模板把顶部姓名、求职意向和联系方式放在文本框中；这些内容
    # 不一定出现在 python-docx 的 paragraph/table API 里，因此额外合并高信号 XML 文本。
    for text in _xml_fallback_chunks(xml_chunks, seen):
        add_text(text)

    if len(body_text.strip()) < 100 and len("\n".join(xml_chunks).strip()) > len(body_text.strip()):
        return "\n".join(_merge_label_value_lines(xml_chunks))
    return "\n".join(_merge_label_value_lines(chunks))


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
    ocr_text, ocr_meta = _ocr_pdf(path)
    if ocr_text.strip():
        warnings.append("已尝试 OCR 兜底提取文本。")
        avg_conf = float(ocr_meta.get("avg_confidence") or 0)
        kept = int(ocr_meta.get("kept_lines") or 0)
        dropped = int(ocr_meta.get("dropped_lines") or 0)
        if avg_conf and avg_conf < 0.7:
            warnings.append(f"OCR 平均置信度偏低（{avg_conf:.2f}），部分文字可能识别不准。")
        if dropped >= 3 and kept > 0:
            warnings.append(f"已过滤 {dropped} 行低置信 OCR 结果，仅保留较可靠文本。")
        if _junk_text_ratio(ocr_text) >= 0.35:
            warnings.append("OCR 文本噪声较高，建议改用可选中文本的 PDF/DOCX。")
        return ocr_text, warnings
    warnings.append("OCR 未能提取有效文本，请检查文件是否为清晰扫描件。")
    return text, warnings


def _ocr_pdf(path: Path) -> tuple[str, dict[str, Any]]:
    """OCR 提取并按置信度过滤（底层加固：宁缺毋滥）。"""
    try:
        import numpy as np
        import pdfplumber
        from paddleocr import PaddleOCR
    except Exception:
        return "", {"avg_confidence": 0.0, "kept_lines": 0, "dropped_lines": 0}

    ocr = _get_ocr_engine(PaddleOCR)
    if ocr is None:
        return "", {"avg_confidence": 0.0, "kept_lines": 0, "dropped_lines": 0}

    chunks: list[str] = []
    confidences: list[float] = []
    dropped = 0
    min_conf = 0.55
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                image = page.to_image(resolution=180).original
                result = ocr.ocr(np.array(image), cls=True)
                for page_result in result or []:
                    for line in page_result or []:
                        if len(line) < 2 or not line[1]:
                            continue
                        payload = line[1]
                        text = str(payload[0]).strip() if payload else ""
                        try:
                            conf = float(payload[1]) if len(payload) > 1 else 1.0
                        except (TypeError, ValueError):
                            conf = 1.0
                        if not text:
                            continue
                        if conf < min_conf:
                            dropped += 1
                            continue
                        chunks.append(text)
                        confidences.append(conf)
    except Exception:
        return "", {"avg_confidence": 0.0, "kept_lines": 0, "dropped_lines": dropped}
    avg_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
    return "\n".join(chunks), {
        "avg_confidence": avg_conf,
        "kept_lines": len(chunks),
        "dropped_lines": dropped,
    }


_ocr_engine = None
_ocr_lock = __import__("threading").Lock()


def _get_ocr_engine(paddle_ocr_cls: Any) -> Any | None:
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            try:
                _ocr_engine = paddle_ocr_cls(use_angle_cls=True, lang="ch", show_log=False)
            except Exception:
                return None
    return _ocr_engine


def detect_sections(text: str) -> dict[str, list[str]]:
    raw_lines = _expand_resume_lines(text)
    sections = {key: [] for key in SECTION_KEYS}
    current = "basic_info"
    seen_heading = False

    for line in raw_lines:
        heading = _detect_heading_section(line)
        if heading:
            seen_heading = True
            current = heading
            if not _is_pure_heading_line(line, heading) and not _is_empty_section_value(line, heading):
                sections[current].append(line)
            continue

        inferred = _infer_content_section(line, current)
        # 仅在允许切换时更新 current；拒绝切换时不得写入误推断桶
        if inferred and _should_switch_section(line, current, inferred, seen_heading):
            current = inferred
        sections[current].append(line)

    return _refine_sections(_dedupe_sections(sections), text)


def _expand_resume_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        normalized = _normalize_line(line)
        if not normalized:
            continue
        # 兼容表格导出：|、全角｜、制表符
        if re.search(r"\s\|\s|｜|\t", normalized):
            parts = [part.strip() for part in re.split(r"\s*\|\s*|｜|\t+", normalized) if part.strip()]
        else:
            parts = [normalized]
        for part in parts:
            lines.extend(_split_inline_heading_segments(part))
    return _merge_label_value_lines(lines)


def _xml_fallback_chunks(xml_chunks: list[str], existing: set[str]) -> list[str]:
    selected: list[str] = []
    selected_indexes: set[int] = set()
    for index, text in enumerate(xml_chunks):
        if text in existing or not _is_high_signal_xml_text(text):
            continue
        for nearby in (index - 1, index, index + 1):
            if nearby < 0 or nearby >= len(xml_chunks) or nearby in selected_indexes:
                continue
            candidate = xml_chunks[nearby]
            if candidate in existing:
                continue
            if nearby != index and not _is_probable_field_value(candidate):
                continue
            selected.append(candidate)
            selected_indexes.add(nearby)
    return selected


def _is_high_signal_xml_text(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if _is_label_only_line(compact) or CONTACT_RE.search(text) or EMAIL_RE.search(text) or PHONE_RE.search(text):
        return True
    return bool(
        re.search(
            r"(求职意向|目标岗位|应聘岗位|期望岗位|期望薪资|基本信息|教育背景|主修课程|新媒体运营|小红书|淘宝运营|SEO|SEM|PS|PR|AE)",
            text,
            re.IGNORECASE,
        )
    )


def _is_probable_field_value(text: str) -> bool:
    clean = _normalize_line(text)
    if not clean or len(clean) > 80:
        return False
    if _detect_heading_section(clean):
        return False
    if EMAIL_RE.search(clean) or PHONE_RE.search(clean):
        return True
    return bool(re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", clean))


def _merge_label_value_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    index = 0
    while index < len(lines):
        line = _normalize_line(lines[index])
        if not line:
            index += 1
            continue
        if _is_label_only_line(line) and index + 1 < len(lines):
            next_line = _normalize_line(lines[index + 1])
            if _is_probable_field_value(next_line):
                merged.append(f"{line.rstrip(':：')}：{next_line}")
                index += 2
                continue
        merged.append(line)
        index += 1
    return merged


def _is_label_only_line(line: str) -> bool:
    key = re.sub(r"\s+", "", line).strip("：:")
    return key.lower() in LABEL_VALUE_FIELDS


def _split_inline_heading_segments(line: str) -> list[str]:
    """拆分特殊模板抽取出的长行，例如“实习 ... 专业技能 ... 自我评价 ...”."""
    if len(line) < 24:
        return [line]
    positions: set[int] = set()
    for marker in INLINE_HEADING_MARKERS:
        start = 0
        while True:
            index = line.find(marker, start)
            if index < 0:
                break
            start = index + len(marker)
            if index == 0:
                continue
            before = line[index - 1]
            after = line[index + len(marker) : index + len(marker) + 1]
            if before in " 　,，;；。|/、)" and (not after or after in " 　:：,，;；"):
                positions.add(index)
    if not positions:
        return [line]
    ordered = [0] + sorted(positions) + [len(line)]
    segments = [line[ordered[i] : ordered[i + 1]].strip(" ，,；;。") for i in range(len(ordered) - 1)]
    return [segment for segment in segments if segment]


def extract_skill_phrases(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for pattern in TECH_SKILL_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            token = match.group(0).strip()
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(token)
    return found


def extract_contact_entities(text: str) -> dict[str, str]:
    entities: dict[str, str] = {}
    expanded_text = "\n".join(_expand_resume_lines(text))
    search_text = re.sub(r"(?<=[\u4e00-\u9fa5])[ \t]+(?=[\u4e00-\u9fa5])", "", expanded_text)
    email_match = EMAIL_RE.search(search_text)
    if email_match:
        entities["email"] = email_match.group(0)
    phone_match = PHONE_RE.search(search_text)
    if phone_match:
        phone = re.sub(r"\D", "", phone_match.group(0))
        entities["phone"] = phone[2:] if phone.startswith("86") and len(phone) == 13 else phone
    wechat_match = WECHAT_RE.search(search_text)
    if wechat_match:
        entities["wechat"] = wechat_match.group(1)
    qq_match = QQ_RE.search(search_text)
    if qq_match:
        entities["qq"] = qq_match.group(1)
    salary_match = SALARY_RE.search(search_text)
    if salary_match:
        entities["expected_salary"] = salary_match.group(1)
    location_match = LOCATION_RE.search(search_text)
    if location_match:
        entities["location"] = location_match.group(1)
    return entities


def extract_name_hint(sections: dict[str, list[str]], text: str) -> str:
    label_match = NAME_LABEL_RE.search(text)
    if label_match:
        candidate = label_match.group(1).strip()
        if _looks_like_person_name(candidate):
            return candidate

    for line in sections.get("basic_info", []) + sections.get("summary", []):
        clean = _normalize_line(line)
        label_inline = NAME_LABEL_RE.search(clean)
        if label_inline and _looks_like_person_name(label_inline.group(1)):
            return label_inline.group(1).strip()
        if _looks_like_person_name(clean):
            return clean

    for line in text.splitlines()[:12]:
        clean = _normalize_line(line)
        if _looks_like_person_name(clean):
            return clean
        # 表格行常见：成娇 | 女 | 本科
        for part in clean.split("|"):
            part = part.strip()
            if _looks_like_person_name(part):
                return part
    return ""


def _looks_like_person_name(value: str) -> bool:
    clean = _normalize_line(value)
    if not clean or clean in RESUME_NOISE_WORDS:
        return False
    if CONTACT_RE.search(clean) or EMAIL_RE.search(clean):
        return False
    if _detect_heading_section(clean):
        return False
    if re.search(r"\d{4}|简历|大学|学院|专业|意向|岗位|求职", clean):
        return False
    # 专业/学科短词（如「人力资源管理」）不是姓名
    if MAJOR_HINT_RE.search(clean) and len(clean) >= 4:
        return False
    if NAME_HINT_RE.match(clean):
        return True
    return False


def extract_keywords(text: str, limit: int = 30) -> list[str]:
    phrase_hits = extract_skill_phrases(text)
    seen = {word.lower() for word in phrase_hits}
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
        key = word.lower()
        if key in seen:
            continue
        counts[word] = counts.get(word, 0) + 1
    ranked = [word for word, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)]
    merged = phrase_hits + ranked
    return merged[:limit]


def detect_target_from_filename(stem: str) -> str:
    """从文件名括号/分隔符中提取求职方向（常见于「姓名-求职简历(岗位).docx」）。"""
    bracket = re.search(r"[（(【\[]([^)）】\]]+)[)）】\]]", stem)
    if bracket:
        cleaned = _clean_target_position(bracket.group(1).replace("-", "、"))
        if cleaned:
            return cleaned
    for part in re.split(r"[-_—]", stem):
        part = part.strip()
        if any(token in part for token in ("设计", "运营", "开发", "分析", "剪辑", "产品", "市场", "实习")):
            cleaned = _clean_target_position(part)
            if cleaned:
                return cleaned
    return ""


def detect_target_position(text: str, sections: dict[str, list[str]]) -> str:
    candidates = list(sections.get("summary", []))
    candidates.extend(_expand_resume_lines(text))
    candidates = list(dict.fromkeys(line.strip() for line in candidates if line.strip()))
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
    experience_present = bool(sections.get("internship") or sections.get("projects") or sections.get("campus"))
    # 五个核心键出现数量（兼容旧口径）
    core_keys_hit = sum(1 for key in core_keys if sections.get(key))
    warnings = list(dict.fromkeys(parser_warnings))
    used_ocr = any("OCR" in item for item in warnings)
    junk_ratio = _junk_text_ratio(stripped)
    has_contact = bool(CONTACT_RE.search(stripped) or EMAIL_RE.search(stripped) or PHONE_RE.search(stripped))

    if not stripped:
        warnings.append("未能从文件中提取到正文，可能是图片版简历、文本框版式或文件损坏。")
    elif len(stripped) < 120:
        warnings.append("提取到的正文较短，评分仅供参考。")
    if core_keys_hit <= 1:
        warnings.append("核心模块识别不足，可能存在特殊排版或图片化内容。")
    elif core_keys_hit <= 2:
        warnings.append("部分核心模块识别不足，建议核对解析结果。")
    if suffix == ".docx" and len(stripped) < 80:
        warnings.append("DOCX 可能使用了特殊模板、文本框或图片内容，建议另存为标准 DOCX/PDF 后重试。")
    if junk_ratio >= 0.4:
        warnings.append("正文噪声偏高（乱码/碎片行较多），解析结果请人工核对。")
    if not has_contact and len(stripped) >= 120:
        warnings.append("未识别到明确联系方式，可检查是否被放在图片或页眉中。")

    hard_fail = (not stripped) or len(stripped) < 80 or core_keys_hit <= 1 or junk_ratio >= 0.55
    if hard_fail:
        return "low", warnings

    # OCR 或轻度告警不直接封顶 medium：内容够完整仍可 high
    soft_only = bool(warnings) and all(
        any(token in item for token in ("OCR", "联系方式", "噪声"))
        for item in warnings
    )
    strong_structure = (
        len(stripped) >= 280
        and core_keys_hit >= 3
        and bool(sections.get("education"))
        and experience_present
        and bool(sections.get("skills") or sections.get("projects"))
        and junk_ratio < 0.25
    )
    if strong_structure and (not warnings or soft_only) and (not used_ocr or junk_ratio < 0.2):
        return "high", warnings
    if len(stripped) < 300 or core_keys_hit <= 2 or warnings or used_ocr:
        return "medium", warnings
    return "high", warnings


def estimate_layout_complexity(text: str) -> float:
    """Estimate layout irregularity without treating complexity as quality failure."""
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return 0.0
    short_ratio = sum(1 for line in lines if len(line) <= 4) / max(len(lines), 1)
    table_lines = sum(1 for line in lines if " | " in line or "\t" in line or "｜" in line)
    sticky_lines = sum(1 for line in lines if len(line) > 120)
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


def _junk_text_ratio(text: str) -> float:
    """估计碎片/噪声行占比，辅助 OCR 与坏版式质量判定。"""
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return 1.0
    junk = 0
    for line in lines:
        compact = re.sub(r"\s+", "", line)
        if len(compact) <= 1:
            junk += 1
            continue
        # 大量孤立符号/无汉字无字母数字
        if not re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", compact):
            junk += 1
            continue
        # 过碎：整行几乎全是单字空格
        if len(line) >= 6 and line.count(" ") >= max(3, len(compact) // 2):
            junk += 1
    return round(junk / max(len(lines), 1), 3)


def _build_heading_index() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for key, aliases in SECTION_PATTERNS.items():
        for alias in aliases:
            entries.append((alias.lower(), key))
    for key, aliases in SECTION_PATTERNS_EN.items():
        for alias in aliases:
            entries.append((alias.lower(), key))
    entries.sort(key=lambda item: len(item[0]), reverse=True)
    return entries


HEADING_INDEX = _build_heading_index()


def _detect_heading_section(line: str) -> str:
    clean = _normalize_heading(line)
    if not clean or len(clean) > 40:
        return ""

    clean_lower = clean.lower()
    for alias, key in HEADING_INDEX:
        if not _heading_matches(clean_lower, alias):
            continue
        resolved = _resolve_detected_heading(key, clean, alias)
        if resolved:
            return resolved
    return ""


def _resolve_detected_heading(key: str, clean: str, alias: str) -> str:
    """消歧义：荣誉/课堂实践/字段值不应落入实习标题。"""
    if key == "internship":
        if re.search(r"(荣誉|优秀|奖项|奖学金|运动会|表彰|先进|标兵|提名)", clean):
            return "awards"
        if re.search(r"(项目|课堂|课程)", clean) and re.search(r"(实践|经历|实训)", clean):
            return "projects"
        if re.search(r"(校园|社团|志愿|学生会|学生工作|在校)", clean):
            return "campus"
        # 「(社会实践)」是角色后缀，不是板块标题
        if re.fullmatch(r"[（(【\[]?社会实践[)）】\]]?", clean):
            return ""
        # 「工作经验：一年」等短字段值
        if _is_heading_field_value(clean, alias):
            return ""
        return "internship"
    if key in {"awards", "skills", "education", "basic_info"} and _is_heading_field_value(clean, alias):
        # 「荣誉：无」仍可当 awards 空值标题；短字段保留原 key 由后续空值逻辑处理
        if key == "awards" and re.search(r"(无|暂无|没有|待补充)$", clean):
            return "awards"
    return key


def _is_heading_field_value(clean: str, alias: str) -> bool:
    """标题后紧跟短字段值（如 工作经验：一年）不是板块切换标题。"""
    alias_lower = alias.lower()
    clean_lower = clean.lower()
    for sep in ("：", ":"):
        prefix = f"{alias_lower}{sep}"
        if not clean_lower.startswith(prefix):
            continue
        remainder = clean[len(alias) + 1 :].strip()
        if not remainder:
            return False
        if len(remainder) <= 12 and not re.search(
            r"(经历|经验|实习|项目|公司|集团|医院|负责|参与)", remainder
        ):
            return True
    return False


def _heading_matches(clean: str, alias: str) -> bool:
    alias_lower = alias.lower()
    clean_lower = clean.lower()
    if clean_lower == alias_lower:
        return True
    if clean_lower.startswith(f"{alias_lower}：") or clean_lower.startswith(f"{alias_lower}:"):
        if _is_heading_field_value(clean, alias):
            return False
        return True
    if clean_lower.endswith(alias_lower) and len(clean_lower) <= len(alias_lower) + 4:
        # 「三下乡社会实践」「社会实践荣誉」等：别名被嵌在荣誉短语里时交给 resolve
        return True
    # 短别名（工作/实习/技能…）禁止句中包含匹配，避免「相关工作」被当成标题
    if len(alias_lower) <= 2:
        return False
    if alias_lower in clean_lower and len(clean_lower) <= max(len(alias_lower) + 6, 18):
        return True
    if alias in {"项目一", "项目二", "项目三"} and alias in clean:
        return True
    return False


def _is_pure_heading_line(line: str, section_key: str) -> bool:
    clean = _normalize_heading(line)
    if not clean:
        return True
    aliases = SECTION_PATTERNS.get(section_key, []) + SECTION_PATTERNS_EN.get(section_key, [])
    clean_lower = clean.lower().strip("：:")
    return any(clean_lower == alias.lower().strip("：:") for alias in aliases)


def _infer_content_section(line: str, current: str) -> str:
    if CONTACT_RE.search(line):
        return "basic_info"
    if _is_job_intent_line(line):
        return "basic_info"
    if current in {"internship", "campus"} and _is_embedded_experience_honor(line):
        return current
    if current == "education" and _is_embedded_education_honor(line):
        return "education"
    if _is_award_line(line) or AWARD_CONTEXT_RE.search(line):
        return "awards"
    # 学生组织优先；校园产品型项目由 _is_campus_line 排除后走 projects
    if _is_campus_line(line):
        return "campus"
    if _is_project_line(line) and current not in {"internship"}:
        return "projects"
    # 经历块内的技能词（如「使用 PS 完成…」）不跳出到 skills
    if SKILL_RE.search(line) and current not in {"projects", "internship", "education", "campus"}:
        return "skills"
    if _is_summary_line(line, current):
        return "summary"
    # 实习/公司优先于「项目」关键词，避免实习描述被项目抢走
    if _is_internship_line(line) and current not in {"education", "skills", "awards"}:
        return "internship"
    if DATE_RANGE_RE.search(line) and SCHOOL_RE.search(line):
        return "education"
    if DATE_RANGE_RE.search(line) and ORG_RE.search(line):
        return "internship"
    if SCHOOL_RE.search(line) and current not in {"skills", "projects", "internship"}:
        return "education"
    return ""


def _should_switch_section(line: str, current: str, inferred: str, seen_heading: bool) -> bool:
    if inferred == current:
        return False
    if _looks_like_heading(line):
        return True
    # 教育块内的专业短行不要被「系统」等项目弱信号抢走
    if current == "education" and inferred == "projects" and not re.search(
        r"(项目|小程序|平台|网站|毕业设计|实训|课题|：|:)", line
    ):
        return False
    # 已在经历块时，普通技能词/空泛评价不要打断
    if current in {"internship", "projects", "campus"} and inferred in {"skills", "summary"}:
        return bool(_looks_like_heading(line) or _detect_heading_section(line) or _is_evaluative_summary_prose(line))
    if inferred in {"projects", "internship"} and (
        DATE_RANGE_RE.search(line) or PROJECT_RE.search(line) or _is_internship_line(line)
    ):
        return True
    if inferred in {"campus", "awards", "summary"}:
        return True
    if not seen_heading and inferred in {"basic_info", "education", "skills"}:
        return True
    if current in {"summary", "basic_info"} and inferred in {"basic_info", "education", "skills", "awards", "campus"}:
        return True
    if current == "summary" and inferred in {"basic_info", "education", "skills", "awards", "campus"}:
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
    clean = re.sub(r"^[■●◆▪▸►【\[\s]+", "", clean)
    clean = re.sub(r"[\]】\s]+$", "", clean)
    clean = re.sub(r"^[（(]?[0-9一二三四五六七八九十]+[）).、．]\s*", "", clean)
    clean = clean.strip("：:|-_ ·•")
    return clean


def _refine_sections(sections: dict[str, list[str]], text: str) -> dict[str, list[str]]:
    """二次整理：纠正无标题简历中错分的行。"""
    refined = {key: list(lines) for key, lines in sections.items()}

    redistributed = {key: [] for key in SECTION_KEYS}
    for source_key in SECTION_KEYS:
        for line in refined.get(source_key, []):
            target = _classify_line_for_refinement(line, source_key)
            redistributed.setdefault(target, []).append(line)
    refined = redistributed

    # 无标题简历：前几行通常是姓名/联系方式
    expanded = _expand_resume_lines(text)
    if not any(_detect_heading_section(line) for line in expanded[:30]):
        for line in expanded[:15]:
            if line in refined.get("basic_info", []):
                continue
            if CONTACT_RE.search(line) or _looks_like_person_name(line):
                refined.setdefault("basic_info", []).append(line)

    return _dedupe_sections(_backfill_cross_section_signals(refined, text))


def _classify_line_for_refinement(line: str, current: str) -> str:
    if _is_job_intent_line(line):
        return "basic_info"
    # Once a summary heading has been seen, keep ordinary prose there. Generic
    # words such as "工作" and "项目" should not turn self-evaluation into
    # experience sections.
    if current == "summary" and not (
        _is_award_line(line)
        or _looks_like_education_only(line)
        or _is_campus_line(line)
        or _is_clear_experience_line(line)
        or (
            _is_skill_list_line(line)
            and _is_skill_line(line, current)
            and not _is_evaluative_summary_prose(line)
        )
    ):
        return "summary"
    if current == "summary" and _is_evaluative_summary_prose(line):
        return "summary"
    if current in {"internship", "campus"} and _is_embedded_experience_honor(line):
        return current
    # 教育段中的奖学金/GPA/排名是嵌入式信息，不单独制造 awards 板块。
    if current == "education" and _is_embedded_education_honor(line):
        return "education"
    # 教育块内的专业短行优先保留，避免被误判为人名/基本信息；长软评价例外
    if current == "education" and (SCHOOL_RE.search(line) or MAJOR_HINT_RE.search(line)):
        if not (
            _is_evaluative_summary_prose(line)
            and not re.search(r"(大学|学院|本科|专科|主修课程|就读|毕业)", line)
        ):
            return "education"
    # 姓名+方向混排（如「赵六 / 数据分析」）归基本信息
    if _looks_like_name_with_direction(line):
        return "basic_info"
    if CONTACT_RE.search(line) or _looks_like_person_name(line):
        return "basic_info"
    if _is_award_line(line) or AWARD_CONTEXT_RE.search(line):
        return "awards"
    if _is_campus_line(line):
        return "campus"
    # 项目标题块内保留；产品型「校园…」不按校园经历搬移
    if current == "projects" and (_is_project_line(line) or not _is_campus_line(line)):
        if _is_internship_line(line) and re.search(r"实习", line) and not re.search(
            r"(实习简历|怎么写|课程作业|个人练习)", line
        ):
            return "internship"
        return "projects"
    if _is_project_line(line) and current != "internship":
        return "projects"
    if _is_internship_line(line):
        return "internship"
    if _is_skill_line(line, current):
        return "skills"
    if _is_summary_line(line, current) or _is_evaluative_summary_prose(line):
        return "summary"
    if SCHOOL_RE.search(line) and not ORG_RE.search(line):
        return "education"
    # 专业短词才归教育；含「网络公司」等机构名的不归教育
    if MAJOR_HINT_RE.search(line) and not ORG_RE.search(line) and not ACTION_RE.search(line):
        return "education"
    return current if current in SECTION_KEYS else "summary"


def _is_campus_line(line: str) -> bool:
    if CAMPUS_ORG_RE.search(line):
        return True
    if not CAMPUS_CONTEXT_RE.search(line):
        return False
    if re.search(r"(学校实训|在校实训)", line):
        return True
    # 「校园二手平台 / 校园跑腿小程序」等属于项目，不是学生工作
    if PROJECT_PRODUCT_RE.search(line):
        return False
    return bool(re.search(r"(活动|组织|策划|实践|任职|担任|经历)", line)) or len(line) <= 24


def _is_award_line(line: str) -> bool:
    if re.search(r"(?:荣誉|奖项|证书)\s*[：:]?\s*(?:无|暂无|没有|待补充)$", line.strip()):
        return False
    if len(line) > 160 and not re.search(r"(个人荣誉|荣誉证书|证书荣誉|获奖情况)", line):
        return False
    # 参与/组织竞赛是活动经历；只有明确的获奖结果才进入荣誉板块。
    if re.search(r"(参与|组织|负责|参加|协助|策划).{0,24}(大赛|竞赛|活动)", line) and not re.search(
        r"(获奖|荣誉|奖学金|一等奖|二等奖|三等奖|提名|称号|优秀(?:学生|团队|个人|志愿者))", line
    ):
        return False
    # 证书等级默认属于技能，不足以证明获得了荣誉；只有明确获奖词才进入 awards。
    if AWARD_RE.search(line):
        return True
    return bool(AWARD_CONTEXT_RE.search(line) and CERTIFICATE_ONLY_RE.search(line))


def _is_empty_section_value(line: str, section_key: str) -> bool:
    if section_key != "awards":
        return False
    return bool(re.search(r"(?:荣誉|奖项|证书)\s*[：:]?\s*(?:无|暂无|没有|待补充)$", line.strip()))


def _is_embedded_education_honor(line: str) -> bool:
    return bool(
        re.search(r"(学业成绩|专业排名|绩点|GPA)", line, re.I)
        and re.search(r"(奖学金|学业表现|排名前|专业前)", line)
    )


def _is_embedded_experience_honor(line: str) -> bool:
    return bool(
        re.search(r"(实习生|医院|患者|科室|公司|团队|部门)", line)
        and re.search(r"(优秀|提名|好评|表彰|荣誉)", line)
    )


def _is_summary_line(line: str, current: str) -> bool:
    if SUMMARY_HEADING_RE.search(line):
        return True
    if current == "summary" and (SUMMARY_SOFT_RE.search(line) or _is_evaluative_summary_prose(line)):
        return True
    # 乱序标题后置：以「本人/具备/热爱…」开头的软评价可切入 summary
    if current not in {"internship", "projects", "campus"} and SUMMARY_PROSE_START_RE.search(line):
        if not _has_strong_internship_evidence(line) and not _is_award_line(line):
            return True
    return False


def _is_evaluative_summary_prose(line: str) -> bool:
    """识别自我评价正文（含标题后置的乱序软段落）。"""
    text = (line or "").strip()
    if not text or len(re.sub(r"\s+", "", text)) < 10:
        return False
    if _is_award_line(text) or _looks_like_education_only(text):
        return False
    if _is_job_intent_line(text):
        return False
    if re.search(r"(实习简历|怎么写|课程作业|个人练习作品)", text):
        return False
    # 技能清单 / 「熟练使用…」主导行优先归 skills，不进 summary
    if re.match(r"^(?:[-–—•·\s]*)(?:熟练|掌握|了解|办公软件|证书)", text) and not SUMMARY_PROSE_START_RE.search(text):
        return False
    if _is_skill_list_line(text) and SKILL_RE.search(text) and not SUMMARY_PROSE_START_RE.search(text):
        if not re.search(r"(性格|为人|责任心|团队协作|抗压|共情)", text):
            return False
    if SUMMARY_PROSE_START_RE.search(text):
        return True
    if SUMMARY_SOFT_RE.search(text) and len(re.sub(r"\s+", "", text)) >= 16:
        return True
    if re.search(r"(责任心|团队意识|抗压能力|适应能力|共情|岗位适配|综合素养)", text) and len(text) >= 16:
        return True
    return False


def _regex_hits_non_overlapping(line: str, first: re.Pattern[str], second: re.Pattern[str]) -> bool:
    """要求两个模式命中不同片段，避免「剪辑」同时充当机构词与动作词。"""
    for left in first.finditer(line):
        for right in second.finditer(line):
            if left.end() <= right.start() or right.end() <= left.start():
                return True
    return False


def _is_internship_line(line: str) -> bool:
    if _looks_like_education_only(line):
        return False
    if _is_job_intent_line(line):
        return False
    if _is_skill_list_line(line) and not re.search(r"(实习|intern|公司|集团)", line, re.I):
        return False
    if _is_profile_skill_line(line):
        return False
    if _is_evaluative_summary_prose(line) and not re.search(r"(实习|intern|公司|集团|医院)", line, re.I):
        return False
    if re.match(r"^\s*\d+[、.)．]", line) and re.search(r"(奖学金|表彰|运动会|优秀团|优秀个人|优秀团队)", line):
        return False
    if re.search(r"(课程作业|个人练习|自学|模仿).{0,20}(实习简历|练习|作品|笔记)", line):
        return False
    if re.search(r"(实习简历|大学生实习|怎么写)", line):
        return False
    # 「希望从事运营相关工作」属于意向，不是实习经历
    if re.search(r"(希望|意向|求职|期望).{0,12}(从事|岗位|工作|方向)", line):
        return False
    if re.search(r"(实习|intern)", line, re.I) and (
        ACTION_RE.search(line)
        or re.search(r"(公司|集团|工作室|助理|岗位|职位|暑期|backend|frontend|产品|测试|运营|设计|开发|医院|护士)", line, re.I)
        or len(line) >= 10
    ):
        return True
    if DATE_RANGE_RE.search(line) and ORG_RE.search(line) and not _looks_like_campus_role_line(line):
        # 排除「2024至今 酒店管理与数字化运营」这类教育行
        if _looks_like_education_only(line):
            return False
        if not re.search(r"(公司|集团|有限公司|股份公司|医院|工作室|实习)", line, re.I):
            return False
        return True
    if re.match(r"^(实习|工作|岗位实践|工作实践)[：:\s]", line):
        return True
    # 需有明确组织实体，避免「酒店管理…运营」专业名被当成实习
    if re.search(r"(公司|集团|工作室|有限公司|股份公司|医院)", line) and ACTION_RE.search(line):
        return True
    # 职责句必须带公司/实习/日期等强证据，避免自我评价「完成…制作」误检
    if re.search(r"(负责|协助|配合|完成).{0,28}(工作|任务|素材|图片|运营|设计|处理|制作|物料|报表|客服|销售)", line):
        return bool(
            re.search(r"(公司|集团|实习|intern|医院|工作室|有限公司|股份公司)", line, re.I)
            or DATE_RANGE_RE.search(line)
        )
    return False


def _has_strong_internship_evidence(line: str) -> bool:
    text = (line or "").strip()
    if not text or re.search(r"(实习简历|怎么写|课程作业|个人练习)", text):
        return False
    if _is_job_intent_line(text):
        return False
    if _looks_like_education_only(text):
        return False
    if _looks_like_campus_role_line(text) and not re.search(r"(公司|集团|医院|工作室|有限公司)", text):
        return False
    if re.search(r"(实习|intern)", text, re.I) and not re.search(r"(实习简历|怎么写)", text):
        if re.search(r"(意向|求职|期望|应聘|希望)", text):
            return False
        return True
    if re.search(r"(公司|集团|有限公司|股份公司|医院|工作室)", text) and (
        ACTION_RE.search(text) or DATE_RANGE_RE.search(text) or re.search(r"(任职|担任|岗位|实习生)", text)
    ):
        return True
    # 明确岗位标题行：招聘助理：… / 运营实习生：…
    if re.search(r"(助理|实习生|工程师|设计师|护士)[：:]", text) and len(re.sub(r"\s+", "", text)) >= 6:
        return True
    if re.search(r"(助理|实习生|工程师|设计师|护士)", text) and re.search(
        r"(负责|参与|协助|筛选|安排|完成|接待|撰写|处理)", text
    ):
        return True
    if DATE_RANGE_RE.search(text) and re.search(r"(公司|集团|有限公司|股份公司|医院|工作室)", text):
        return True
    return False


def _looks_like_campus_role_line(line: str) -> bool:
    if re.search(r"(讲解员|研学|团支书|学生会|社团|志愿者|辅导员助理|文体委员|班长|部长|干事)", line):
        return True
    if re.search(r"(担任|任职).{0,16}(班|团|校|社区|协会|书院)", line):
        return True
    return _is_campus_line(line)


def _is_project_line(line: str) -> bool:
    if not PROJECT_RE.search(line):
        return False
    if re.search(r"(期待|希望|渴望|致力于).{0,20}(平台|机会|成长|发展)", line):
        return False
    # 社会实践中的「项目」通常是校园活动/评优名称，不等同于独立项目经历。
    if re.search(r"(社会实践|三下乡|志愿服务|校园活动|实践活动)", line) and not re.search(
        r"(课程项目|毕业设计|项目经历|项目经验|实训项目|系统开发|平台开发|小程序开发)", line
    ):
        return False
    # 运动会「百米/跳远项目」是竞赛荣誉，不是项目经历
    if re.search(r"(运动会|田径|百米|跳远|赛跑|辩论赛)", line) and not re.search(
        r"(课程项目|毕业设计|小程序|平台|系统|实训)", line
    ):
        return False
    if re.search(r"(主修课程|专业课程|相关课程|课程列表)", line) and not re.search(
        r"(课程项目|课程设计|毕业设计|项目经历|项目经验|实训项目)", line
    ):
        return False
    if _is_award_line(line):
        return False
    # 技能清单里的「剪辑/视频/活动策划」不算项目
    if _is_skill_list_line(line) and not re.search(r"(项目|小程序|平台|毕业设计|课题|实训|系统)", line):
        return False
    if SCHOOL_RE.search(line) and not ACTION_RE.search(line):
        return False
    # 公众号、拍摄、海报等也常出现在实习/校园职责中，不能单独作为项目证据。
    weak_media_signal = re.search(r"(账号|视频号|公众号|社群|短片|海报|片头|包装|拍摄|小红书|抖音|微博)", line)
    explicit_project_signal = re.search(r"(项目|实训|课题|系统|平台|小程序|网站|作品|案例|毕业设计|项目经历|项目经验)", line)
    strong_media_project = re.search(r"(公众号|账号|视频号|小红书|抖音|微博).{0,30}(项目|运营项目|账号项目)", line)
    if weak_media_signal and not strong_media_project and not re.search(r"(运营项目|账号项目)", line):
        return False
    # 文本框/OCR 常把整段自我介绍或工作描述拼成一行；长句中的“项目”不是项目板块证据。
    compact = re.sub(r"\s+", "", line)
    project_title_signal = re.search(
        r"^(?:[·•\-—【\[]?\s*)?(?:20\d{2}[^\n]{0,18})?"
        r"(?:项目经历|项目经验|课程项目|毕业设计|实训项目|项目作品|个人作品|作品集|"
        r"[^：:]{1,30}(?:项目|小程序|平台|系统|网站|课题))\s*[：:|｜]",
        compact,
        re.IGNORECASE,
    )
    if len(compact) > 100 and not project_title_signal:
        return False
    # 「信息管理与信息系统」等专业名含「系统/管理」，无交付信号则非项目
    strong_project = re.search(
        r"(项目|小程序|平台|网站|毕业设计|实训|课题|：|:|负责|完成|参与|开发|实现|上线|搭建)",
        line,
    )
    if MAJOR_HINT_RE.search(line) and not strong_project and len(re.sub(r"\s+", "", line)) <= 18:
        return False
    return True


def _is_skill_line(line: str, current: str) -> bool:
    if current in {"projects", "internship", "campus"} and (
        ACTION_RE.search(line) or re.search(r"(实习|intern|项目|小程序|平台)", line, re.I)
    ):
        return False
    if re.search(r"(专业技能|职业技能|办公软件|设计剪辑|技能专长|技能清单)", line):
        return True
    if len(line) <= 180 and SKILL_RE.search(line):
        return True
    return False


def _looks_like_name_with_direction(line: str) -> bool:
    clean = _normalize_line(line)
    match = re.match(r"^([\u4e00-\u9fa5·]{2,4})\s*[|/／]\s*(.+)$", clean)
    if not match:
        return False
    name, direction = match.group(1), match.group(2)
    if MAJOR_HINT_RE.search(name):
        return False
    return len(direction) <= 16 and not CONTACT_RE.search(clean)


def _is_profile_skill_line(line: str) -> bool:
    """Recognize labeled skill prose outside an actual work/education record."""
    if DATE_RANGE_RE.search(line) or re.search(r"(公司|集团|工作室|实习|任职)", line, re.I):
        return False
    return bool(
        re.match(
            r"^(新媒体运营|视频剪辑|平面设计|办公软件|综合能力|内容创作|排版与设计|平台熟悉度|计算机技能|外语技能)\s*[：:]",
            line,
            re.I,
        )
    )


def _is_clear_experience_line(line: str) -> bool:
    return bool(
        DATE_RANGE_RE.search(line)
        or re.search(r"(实习|intern|公司|集团|工作室|任职于|担任)", line, re.I)
        or re.search(r"^(负责|参与|协助|主导|完成|开发|搭建|上线)\b", line)
    )


def _backfill_cross_section_signals(sections: dict[str, list[str]], text: str = "") -> dict[str, list[str]]:
    """纠偏优先「搬移」误归类行，避免旧逻辑到处复制造成重复计分。"""
    refined = {key: list(lines) for key, lines in sections.items()}

    def _move(line: str, source: str, target: str) -> None:
        if source == target:
            return
        if line in refined.get(source, []):
            refined[source] = [item for item in refined[source] if item != line]
        refined.setdefault(target, [])
        if line not in refined[target]:
            refined[target].append(line)

    # 1) 把明显教育/获奖从错桶搬回
    for source in list(refined.keys()):
        for line in list(refined.get(source) or []):
            if source != "education" and _looks_like_education_only(line) and source in {
                "basic_info",
                "summary",
                "skills",
                "campus",
            }:
                _move(line, source, "education")
            elif source != "awards" and _is_award_line(line) and source in {
                "skills",
                "summary",
                "basic_info",
                "projects",
                "internship",
            }:
                _move(line, source, "awards")

    # 2) 从长实习行尾/获奖行头回收学校与学历（模板简历常见粘连）
    _recover_education_fragments(refined)

    # 3) 仅当目标板块为空时，才做轻量补齐，防止漏识别
    all_lines = [line for lines in refined.values() for line in lines]
    if not refined.get("education"):
        for line in all_lines:
            if _looks_like_education_only(line):
                refined.setdefault("education", []).append(line)
                break
    if not refined.get("internship"):
        for line in all_lines:
            if _has_strong_internship_evidence(line):
                refined.setdefault("internship", []).append(line)
                break
    if not refined.get("skills"):
        for line in all_lines:
            if _is_skill_line(line, "") and not _is_award_line(line) and not _looks_like_education_only(line):
                refined.setdefault("skills", []).append(line)
                break

    # 4) 乱序简历：自我评价正文常在标题之前，或夹带技能词导致被清空
    _recover_disordered_summary(refined, text)

    # 5) 实习多检：无公司/实习强证据时降级为校园/技能/荣誉
    _sanitize_weak_internship_section(refined)

    # 6) 技能/证书行从 summary 拆回；奖项标题下的证书补 awards
    _rebalance_skills_and_awards(refined, text)

    return refined


def _rebalance_skills_and_awards(sections: dict[str, list[str]], text: str) -> None:
    expanded = _expand_resume_lines(text)
    saw_awards = any(_detect_heading_section(line) == "awards" for line in expanded)
    saw_skills = any(_detect_heading_section(line) == "skills" for line in expanded)

    for line in list(sections.get("summary") or []):
        skill_dominant = bool(
            re.match(r"^(?:[-–—•·\s]*)(?:熟练|掌握|了解|办公软件|证书)", line)
            or (_is_skill_list_line(line) and SKILL_RE.search(line) and not SUMMARY_PROSE_START_RE.search(line))
        )
        if skill_dominant and not SUMMARY_PROSE_START_RE.search(line):
            sections["summary"] = [item for item in sections["summary"] if item != line]
            sections.setdefault("skills", [])
            if line not in sections["skills"]:
                sections["skills"].append(line)

    if not sections.get("skills") and saw_skills:
        for source in ("education", "basic_info", "summary"):
            for line in list(sections.get(source) or []):
                if _is_skill_line(line, "") and not _looks_like_education_only(line):
                    sections[source] = [item for item in sections[source] if item != line]
                    sections.setdefault("skills", []).append(line)
                    break
            if sections.get("skills"):
                break

    if not sections.get("awards") and saw_awards:
        for source in ("skills", "education", "basic_info", "campus"):
            for line in list(sections.get(source) or []):
                if CERTIFICATE_ONLY_RE.search(line) or re.search(
                    r"(计算机[一二三]级|普通话|奖学金|优秀|竞赛|奖)", line
                ):
                    if _is_job_intent_line(line) or _has_strong_internship_evidence(line):
                        continue
                    sections[source] = [item for item in sections[source] if item != line]
                    sections.setdefault("awards", []).append(line)
                    break
            if sections.get("awards"):
                break


def _recover_disordered_summary(sections: dict[str, list[str]], text: str) -> None:
    """标题后置/OCR 碎裂时，围绕自我评价标题回收软评价正文。"""
    expanded = _expand_resume_lines(text)
    heading_idxs = [
        idx
        for idx, line in enumerate(expanded)
        if SUMMARY_HEADING_RE.search(line) or _detect_heading_section(line) == "summary"
    ]
    if not heading_idxs and sections.get("summary"):
        return

    recovered: list[str] = []

    def _accept(line: str) -> bool:
        if not line or SUMMARY_HEADING_RE.search(line) and len(re.sub(r"\s+", "", line)) <= 8:
            return False
        if _is_award_line(line) or _has_strong_internship_evidence(line) or _is_project_line(line):
            return False
        if _looks_like_education_only(line) and not _is_evaluative_summary_prose(line):
            return False
        if _is_evaluative_summary_prose(line):
            return True
        # 标题后的短续行（OCR 断行）
        return bool(SUMMARY_SOFT_RE.search(line) and len(re.sub(r"\s+", "", line)) >= 8)

    for idx in heading_idxs:
        # 标题前：乱序双栏常见「正文 → 自我评价」
        for j in range(idx - 1, max(-1, idx - 8), -1):
            line = expanded[j]
            if _detect_heading_section(line) and _detect_heading_section(line) != "summary":
                break
            if _accept(line):
                recovered.append(line)
            elif recovered:
                break
        # 标题后：允许夹带「熟练掌握」的评价句
        for j in range(idx + 1, min(len(expanded), idx + 8)):
            line = expanded[j]
            heading = _detect_heading_section(line)
            if heading and heading != "summary":
                break
            if _accept(line) or (
                len(re.sub(r"\s+", "", line)) >= 12
                and re.search(r"(具备|善于|热爱|期待|责任心|沟通|适应|严谨|共情)", line)
                and not _has_strong_internship_evidence(line)
                and not _is_award_line(line)
            ):
                recovered.append(line)
            elif sections.get("summary") and line in (sections.get("summary") or []):
                continue
            else:
                # 纯技能清单则停止向后扩展
                if _is_skill_list_line(line) and not _is_evaluative_summary_prose(line):
                    break

    # 无标题但全文有明显自我评价段时也补一次
    if not heading_idxs:
        for line in expanded:
            if _is_evaluative_summary_prose(line) and SUMMARY_PROSE_START_RE.search(line):
                recovered.append(line)
                break

    if not recovered and sections.get("summary"):
        return

    # 从其他桶搬移，避免复制计分
    bucket_lines = {line: key for key, lines in sections.items() for line in lines}
    for line in recovered:
        source = bucket_lines.get(line)
        if source and source != "summary":
            sections[source] = [item for item in sections[source] if item != line]
        sections.setdefault("summary", [])
        if line not in sections["summary"]:
            sections["summary"].append(line)
            bucket_lines[line] = "summary"


def _sanitize_weak_internship_section(sections: dict[str, list[str]]) -> None:
    """无公司/实习强证据时，把误入实习的校园职责/技能/荣誉拆回。"""
    lines = list(sections.get("internship") or [])
    if not lines:
        return

    strong = [line for line in lines if _has_strong_internship_evidence(line)]
    if strong:
        kept: list[str] = []
        for line in lines:
            if _is_award_line(line) and not _has_strong_internship_evidence(line):
                sections.setdefault("awards", [])
                if line not in sections["awards"]:
                    sections["awards"].append(line)
                continue
            if _is_profile_skill_line(line) and not _has_strong_internship_evidence(line):
                sections.setdefault("skills", [])
                if line not in sections["skills"]:
                    sections["skills"].append(line)
                continue
            kept.append(line)
        sections["internship"] = kept
        return

    # 完全没有强证据：整桶降级
    for line in lines:
        if _looks_like_campus_role_line(line) or re.search(r"(社会实践|志愿|辅导员|讲解|研学)", line):
            sections.setdefault("campus", [])
            if line not in sections["campus"]:
                sections["campus"].append(line)
        elif _is_award_line(line) or re.search(r"(荣誉|优秀团队|运动会|奖学金)", line):
            sections.setdefault("awards", [])
            if line not in sections["awards"]:
                sections["awards"].append(line)
        elif _is_profile_skill_line(line) or (_is_skill_line(line, "") and not ACTION_RE.search(line)):
            sections.setdefault("skills", [])
            if line not in sections["skills"]:
                sections["skills"].append(line)
        elif _is_evaluative_summary_prose(line):
            sections.setdefault("summary", [])
            if line not in sections["summary"]:
                sections["summary"].append(line)
        elif _is_project_line(line):
            sections.setdefault("projects", [])
            if line not in sections["projects"]:
                sections["projects"].append(line)
        else:
            # 无证据职责行：意向回基本信息，其余倾向校园实践而非虚增实习
            if _is_job_intent_line(line):
                sections.setdefault("basic_info", [])
                if line not in sections["basic_info"]:
                    sections["basic_info"].append(line)
            else:
                sections.setdefault("campus", [])
                if line not in sections["campus"]:
                    sections["campus"].append(line)
    sections["internship"] = []


def _is_skill_list_line(line: str) -> bool:
    compact = re.sub(r"\s+", "", line)
    if compact.count("、") + compact.count(",") + compact.count("，") >= 2:
        return True
    return bool(re.fullmatch(r"[\u4e00-\u9fa5A-Za-z0-9+#.\-、，,/／\s]{2,40}", line) and "、" in line)


def _recover_education_fragments(sections: dict[str, list[str]]) -> None:
    """从粘连长行中回收学校/学历片段，不覆盖已有干净教育行。"""
    school_re = re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,24}(?:大学|学院|职业技术学院|职业技术大学))")
    degree_re = re.compile(r"^(专科|本科|大专|硕士|博士|研究生)")
    recovered: list[str] = []

    for line in sections.get("internship") or []:
        match = school_re.search(line)
        if match and ACTION_RE.search(line):
            recovered.append(match.group(1))

    for line in sections.get("awards") or []:
        if degree_re.search(line.strip()):
            head = re.split(r"(获得|荣获|证书|称号)", line, maxsplit=1)[0].strip(" ，,;；")
            if head:
                recovered.append(head)
        match = school_re.search(line)
        if match:
            recovered.append(match.group(1))

    if not recovered:
        return
    sections.setdefault("education", [])
    # 清掉明显误入的机构名（含公司）
    sections["education"] = [
        line for line in sections["education"] if not (ORG_RE.search(line) and not school_re.search(line))
    ]
    for item in recovered:
        if item and item not in sections["education"]:
            sections["education"].append(item)


def _looks_like_education_only(line: str) -> bool:
    text = (line or "").strip()
    if not text or CONTACT_RE.search(text):
        return False
    # 技能/证书清单里的「专业资格」不是教育经历
    if re.search(r"(资格证书|技能认证|能力证书|等级证书|证书：|证书:)", text) and not re.search(
        r"(大学|学院).{0,8}(本科|专科|专业|就读|毕业)", text
    ):
        return False
    # Words such as "专业能力" or "专业平台" are common in self-evaluation,
    # but do not constitute education evidence without a school or degree.
    if re.search(r"(期待|平台|沟通|性格|能力)", text) and not re.search(
        r"(就读|毕业|本科|专科|大专|硕士|博士|大学|学院)", text
    ):
        return False
    if ACTION_RE.search(text) and not re.search(r"(就读|毕业于|专业|本科|专科|硕士)", text):
        return False
    if re.search(r"(就读|毕业于|教育背景|主修)", text):
        return True
    if SCHOOL_RE.search(text) and re.search(r"(大学|学院|专业|本科|专科|大专|硕士|博士)", text):
        # 任职于某某学院干事 ≠ 教育；但「学院+专科」与奖项同处一行时仍算教育信号
        if re.search(r"(担任|任职|任|干事|部长)", text) and not re.search(r"(就读|毕业于|专科|本科|硕士|专业)", text):
            return False
        # 「大学英语六级」等证书语境
        if re.search(r"(大学英语|英语[四六]级|计算机[一二三]级)", text) and not re.search(
            r"(就读|毕业于|教育背景|主修课程)", text
        ):
            return False
        return True
    return False


def _is_job_intent_line(line: str) -> bool:
    if re.search(r"(求职意向|意向岗位|目标岗位|应聘岗位|期望岗位|求职方向|期望职位)", line, re.I):
        return True
    if re.search(r"(希望|期望|意向).{0,12}(从事|岗位|工作|方向)", line):
        return True
    for pattern in TARGET_POSITION_PATTERNS:
        if re.search(pattern, line, re.I):
            return True
    return False


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
            canonical = _canonical_line(line)
            if canonical and canonical not in seen:
                cleaned[key].append(line)
                seen.add(canonical)
    return cleaned


def _canonical_line(value: str) -> str:
    """用于去重的保守规范化，不改写实际展示文本。"""
    value = _normalize_line(value)
    value = re.sub(r"[：:；;，,。．.、|｜]+", " ", value)
    return re.sub(r"\s+", "", value).lower()


def _clean_target_position(value: str) -> str:
    cleaned = re.split(r"(?:期望城市|工作地点|薪资要求|期望薪资|薪资|薪酬|到岗时间|实习时间|求职类型|电话|手机|邮箱|微信|现居)", value, maxsplit=1)[0]
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
