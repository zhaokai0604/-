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
        "求职意向",
        "目标岗位",
        "意向岗位",
        "应聘岗位",
        "期望岗位",
        "求职方向",
        "职业目标",
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
ORG_RE = re.compile(r"(公司|集团|工作室|中心|传媒|科技|网络|岗位|职位|实习|助理|运营|编辑|剪辑|销售|客服|教师|影视公司|广告公司|传播公司|文化公司|设计助理|设计师|有限公司|股份公司)")
PROJECT_RE = re.compile(r"(项目|实训|课题|系统|平台|小程序|网站|账号|视频号|公众号|社群|活动策划|作品|案例|短片|视频|海报|片头|包装|剪辑|拍摄|账号运营)")
SKILL_RE = re.compile(r"(技能|证书|熟练|掌握|了解|英语|普通话|Office|Excel|Word|PPT|WPS|Python|SQL|Vue|React|剪映|PS|PR|AE|Canva|秀米|Photoshop|Premiere|HarmonyOS|办公软件|办公自动化|设计剪辑)", re.IGNORECASE)
AWARD_RE = re.compile(r"(获奖|荣誉|奖学金|证书|资格证|等级证|Uskills|优秀|一等奖|二等奖|三等奖|初级|中级|高级)", re.IGNORECASE)
SUMMARY_RE = re.compile(r"(自我评价|个人评价|自我介绍|性格特点|为人|沟通|协调|团队协作|学习能力|执行力|抗压|适应)", re.IGNORECASE)
ACTION_RE = re.compile(r"(负责|参与|协助|配合|完成|执行|制作|处理|运营|维护|撰写|剪辑|设计|拍摄|策划|发布|管理|优化)")
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
NAME_HINT_RE = re.compile(r"^[\u4e00-\u9fa5·]{2,6}$")
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

    ocr = _get_ocr_engine(PaddleOCR)
    if ocr is None:
        return ""

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
            if not _is_pure_heading_line(line, heading):
                sections[current].append(line)
            continue

        inferred = _infer_content_section(line, current)
        if inferred and _should_switch_section(line, current, inferred, seen_heading):
            current = inferred
        target = inferred or current
        sections[target].append(line)

    return _refine_sections(_dedupe_sections(sections), text)


def _expand_resume_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        normalized = _normalize_line(line)
        if not normalized:
            continue
        parts = [part.strip() for part in normalized.split(" | ") if part.strip()] if " | " in normalized else [normalized]
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
    if re.search(r"\d{4}|简历|大学|学院|专业|意向|岗位|求职", clean):
        return False
    if NAME_HINT_RE.match(clean):
        return True
    if re.match(r"^[\u4e00-\u9fa5·]{2,4}$", clean):
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
        if _heading_matches(clean_lower, alias):
            return key
    return ""


def _heading_matches(clean: str, alias: str) -> bool:
    alias_lower = alias.lower()
    clean_lower = clean.lower()
    if clean_lower == alias_lower:
        return True
    if clean_lower.startswith(f"{alias_lower}：") or clean_lower.startswith(f"{alias_lower}:"):
        return True
    if clean_lower.endswith(alias_lower) and len(clean_lower) <= len(alias_lower) + 4:
        return True
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
        return "summary"
    if _is_award_line(line):
        return "awards"
    if _is_campus_line(line):
        return "campus"
    if SKILL_RE.search(line) and current not in {"projects", "internship", "education"}:
        return "skills"
    if _is_summary_line(line, current):
        return "summary"
    if PROJECT_RE.search(line) and not SCHOOL_RE.search(line):
        return "projects"
    # 含学校+日期的一般是教育经历，优先于实习判定
    if DATE_RANGE_RE.search(line) and SCHOOL_RE.search(line):
        return "education"
    if DATE_RANGE_RE.search(line) and ORG_RE.search(line):
        return "internship"
    if _is_internship_line(line) and current not in {"education", "skills", "awards"}:
        return "internship"
    if SCHOOL_RE.search(line) and current not in {"skills", "projects", "internship"}:
        return "education"
    return ""


def _should_switch_section(line: str, current: str, inferred: str, seen_heading: bool) -> bool:
    if inferred == current:
        return False
    if _looks_like_heading(line):
        return True
    if inferred in {"projects", "internship"} and (DATE_RANGE_RE.search(line) or PROJECT_RE.search(line) or _is_internship_line(line)):
        return True
    if inferred in {"campus", "awards"}:
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

    return _dedupe_sections(_backfill_cross_section_signals(refined))


def _classify_line_for_refinement(line: str, current: str) -> str:
    if _is_job_intent_line(line):
        return "summary"
    if CONTACT_RE.search(line) or _looks_like_person_name(line):
        return "basic_info"
    if _is_award_line(line):
        return "awards"
    if _is_campus_line(line):
        return "campus"
    if _is_internship_line(line):
        return "internship"
    if _is_skill_line(line, current):
        return "skills"
    if _is_project_line(line):
        return "projects"
    if _is_summary_line(line, current):
        return "summary"
    if SCHOOL_RE.search(line):
        return "education"
    return current if current in SECTION_KEYS else "summary"


def _is_campus_line(line: str) -> bool:
    return bool(re.search(r"(学生会|社团|班委|团委|志愿者|校园|大学期间|在校期间|校内|校外实践|社会实践)", line))


def _is_award_line(line: str) -> bool:
    if len(line) > 160 and not re.search(r"(个人荣誉|荣誉证书|证书荣誉|获奖情况)", line):
        return False
    return bool(AWARD_RE.search(line))


def _is_summary_line(line: str, current: str) -> bool:
    if re.search(r"(自我评价|个人评价|自我介绍|个人总结|性格特点)", line):
        return True
    return current == "summary" and bool(SUMMARY_RE.search(line))


def _is_internship_line(line: str) -> bool:
    if DATE_RANGE_RE.search(line) and ORG_RE.search(line):
        return True
    if re.match(r"^(实习|工作|岗位实践|工作实践)[：:\s]", line):
        return True
    if ORG_RE.search(line) and ACTION_RE.search(line):
        return True
    if re.search(r"(负责|协助|配合|完成).{0,28}(工作|任务|素材|图片|运营|设计|处理|制作|物料|报表|客服|销售)", line):
        return True
    return False


def _is_project_line(line: str) -> bool:
    if not PROJECT_RE.search(line):
        return False
    if SCHOOL_RE.search(line) and not ACTION_RE.search(line):
        return False
    return True


def _is_skill_line(line: str, current: str) -> bool:
    if current in {"projects", "internship", "campus"} and ACTION_RE.search(line):
        return False
    if re.search(r"(专业技能|职业技能|办公软件|设计剪辑|技能专长|技能清单)", line):
        return True
    if len(line) <= 180 and SKILL_RE.search(line):
        return True
    return False


def _backfill_cross_section_signals(sections: dict[str, list[str]]) -> dict[str, list[str]]:
    refined = {key: list(lines) for key, lines in sections.items()}
    all_lines = [line for lines in sections.values() for line in lines]
    for line in all_lines:
        if SCHOOL_RE.search(line) and not CONTACT_RE.search(line):
            refined.setdefault("education", []).append(line)
        if _is_internship_line(line):
            refined.setdefault("internship", []).append(line)
        if _is_skill_line(line, "") and not _is_award_line(line):
            refined.setdefault("skills", []).append(line)
        if _is_award_line(line):
            refined.setdefault("awards", []).append(line)
        if _is_summary_line(line, "summary") and not _is_internship_line(line):
            refined.setdefault("summary", []).append(line)
    return refined


def _is_job_intent_line(line: str) -> bool:
    if re.search(r"(求职意向|意向岗位|目标岗位|应聘岗位|期望岗位|求职方向|期望职位)", line, re.I):
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
            if line not in seen:
                cleaned[key].append(line)
                seen.add(line)
    return cleaned


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
