from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


OUT = "docs/competition_submission/简析智评国赛作品介绍视频脚本.docx"
BLUE = "2E74B5"
DARK = "1F4D78"
LIGHT = "E8EEF5"
GRAY = "F2F4F7"
RED = "9B1C1C"
GOLD = "7A5A00"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths):
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(sum(widths)))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")
    grid = tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths[idx]))
            tc_w.set(qn("w:type"), "dxa")
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)


def set_run_font(run, name="Calibri", size=11, color=None, bold=False, italic=False):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def style_paragraph(p, before=0, after=6, line=1.25, alignment=None):
    fmt = p.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = line
    if alignment is not None:
        p.alignment = alignment


def add_para(doc, text="", style=None, bold_prefix=None, color=None, after=6):
    p = doc.add_paragraph(style=style)
    style_paragraph(p, after=after)
    if bold_prefix and text.startswith(bold_prefix):
        r = p.add_run(bold_prefix)
        set_run_font(r, size=11, color=color or DARK, bold=True)
        r = p.add_run(text[len(bold_prefix):])
        set_run_font(r, size=11)
    else:
        r = p.add_run(text)
        set_run_font(r, size=11, color=color)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, size={1: 16, 2: 13, 3: 12}[level], color=BLUE if level < 3 else DARK, bold=True)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        style_paragraph(p, after=4, line=1.25)
        r = p.add_run(item)
        set_run_font(r, size=11)


def add_numbered(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Number")
        style_paragraph(p, after=4, line=1.25)
        r = p.add_run(item)
        set_run_font(r, size=11)


def add_table(doc, headers, rows, widths, header_fill=LIGHT, font_size=9.5):
    table = doc.add_table(rows=1, cols=len(headers))
    set_table_geometry(table, widths)
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        set_cell_shading(cell, header_fill)
        p = cell.paragraphs[0]
        style_paragraph(p, after=0, line=1.1, alignment=WD_ALIGN_PARAGRAPH.CENTER)
        r = p.add_run(header)
        set_run_font(r, size=font_size, color=DARK, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            p = cells[i].paragraphs[0]
            style_paragraph(p, after=0, line=1.1)
            r = p.add_run(str(value))
            set_run_font(r, size=font_size)
    set_table_geometry(table, widths)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_callout(doc, label, text, fill=GRAY, color=DARK):
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [9360])
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    p = cell.paragraphs[0]
    style_paragraph(p, after=0, line=1.2)
    r = p.add_run(label + "：")
    set_run_font(r, size=10.5, color=color, bold=True)
    r = p.add_run(text)
    set_run_font(r, size=10.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def configure_styles(doc):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25
    for level, size, color, before, after in [
        (1, 16, BLUE, 18, 10),
        (2, 13, BLUE, 14, 7),
        (3, 12, DARK, 10, 5),
    ]:
        style = doc.styles[f"Heading {level}"]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
    for style_name in ("List Bullet", "List Number"):
        style = doc.styles[style_name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.font.size = Pt(11)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.25


def add_header_footer(doc):
    header = doc.sections[0].header.paragraphs[0]
    style_paragraph(header, after=0)
    r = header.add_run("简析智评｜国赛作品介绍视频脚本")
    set_run_font(r, size=9, color="666666")
    footer = doc.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    style_paragraph(footer, after=0)
    r = footer.add_run("内部拍摄执行稿")
    set_run_font(r, size=9, color="666666")


def scene_table(doc, scene):
    headers = ["时间", "画面与操作", "旁白（可直接照读）", "屏幕字幕 / 拍摄提示"]
    rows = [[scene["time"], scene["visual"], scene["voice"], scene["caption"]]]
    return add_table(doc, headers, rows, [900, 2600, 4000, 1860], font_size=9.2)


def main():
    doc = Document()
    configure_styles(doc)
    add_header_footer(doc)

    p = doc.add_paragraph()
    style_paragraph(p, after=3, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    r = p.add_run("简析智评")
    set_run_font(r, size=28, color=DARK, bold=True)
    p = doc.add_paragraph()
    style_paragraph(p, after=4, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    r = p.add_run("高校就业数据治理闭环与简历评价智能体")
    set_run_font(r, size=18, color=BLUE, bold=True)
    p = doc.add_paragraph()
    style_paragraph(p, after=18, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    r = p.add_run("国赛作品介绍视频脚本｜详细拍摄执行稿")
    set_run_font(r, size=13, color="666666")

    add_callout(doc, "建议版本", "推荐成片时长约 8 分 30 秒；语速按每分钟 220～250 字控制。可根据组委会时长要求，按“精简版 3 分钟”章节压缩。", fill="F4F6F9")
    add_callout(doc, "使用方式", "旁白栏是主持人/配音稿；画面与操作栏是录屏和实拍要求；字幕栏只保留短句、数字和关键词，不把整段旁白铺满屏幕。", fill="F4F6F9")

    add_heading(doc, "一、先核对赛题：视频必须回答什么", 1)
    add_para(doc, "赛题名称为“简历评价智能体-某人才服务公司简历评价与分析”。赛题要求面向高校学生，支持 Word、PDF 等常见格式上传，完成内容解析、信息提取、多维评价、个性化修改建议和岗位匹配度分析，并生成可视化评价报告。作品评价标准为功能完整性 30 分、解析准确性 30 分、评价科学性 30 分、技术创新性 10 分。")
    add_table(doc, ["赛题评分点", "视频必须展示", "本项目对应能力", "本片口径"], [
        ["功能完整性 30 分", "上传、解析、评分、诊断、报告导出", "学生端分析、优化稿 DOCX、报告、批量、教师端", "展示完整闭环，不只展示聊天窗口"],
        ["解析准确性 30 分", "不同格式和版式的内容提取", "DOCX/PDF、结构化分节、OCR 兜底、质量告警", "区分链路成功、文本可读、板块识别"],
        ["评价科学性 30 分", "多维评分、岗位差异化、具体建议", "六维评分、岗位画像、证据片段、硬约束、低信噪比", "规则负责护栏，语义负责匹配，证据负责解释"],
        ["技术创新性 10 分", "算法、推荐、模板、安全与效率", "三擎协同、岗位知识库、技能图谱、SSE、Diff、数据隔离", "创新落在可复核的工程闭环，不夸大模型指标"],
    ], [1700, 2600, 3000, 2060])
    add_callout(doc, "核心判断", "赛题重点不是“模型分数越高越好”，而是能否把简历接入、评价、岗位适配、修改交付和就业指导沉淀成可运行、可解释、可复核的系统。", fill="E8EEF5")

    add_heading(doc, "二、成片总体设计", 1)
    add_table(doc, ["项目", "建议安排"], [
        ["视频定位", "国赛参赛作品介绍 + 产品演示 + 技术与可信边界说明"],
        ["建议时长", "约 8 分 30 秒；如要求更短，保留第 1、2、3、4、7、8 段"],
        ["画面比例", "16:9；网页录屏为主，穿插团队/校园/教师指导场景，避免无关素材"],
        ["叙事主线", "问题提出 → 学生分析 → 岗位适配 → 优化交付 → 教师治理 → 技术与安全 → 总结"],
        ["最终记忆点", "先匹配、再护航、后交付；从一份简历，沉淀为学生成长与教师指导的数据资产"],
    ], [1800, 7560])

    add_heading(doc, "三、正式视频脚本（约 8 分 30 秒）", 1)
    add_heading(doc, "0:00—0:35 片头：从一份简历开始", 2)
    scene_table(doc, {"time":"0:00—0:35", "visual":"黑底/校园实拍切入。展示学生面对简历反复修改、岗位描述和教师批改的镜头。随后出现项目首页和 Logo。", "voice":"对于高校学生来说，简历是走向职场的第一张名片。但在实际求职中，很多简历并不是没有内容，而是内容没有被准确识别，能力没有与岗位对齐，问题也没有得到具体反馈。教师在毕业季又常常面对大量简历，难以兼顾效率和个性化指导。针对这一问题，我们设计了简析智评——高校就业数据治理闭环与简历评价智能体。", "caption":"简历不是只有分数，更需要可解释的成长建议"})

    add_heading(doc, "0:35—1:15 赛题回应：从要求到产品", 2)
    scene_table(doc, {"time":"0:35—1:15", "visual":"画面叠加四个评分点：功能完整性、解析准确性、评价科学性、技术创新性。切换到系统首页，展示学生端、教师端、管理端入口。", "voice":"本作品严格对应赛题要求：支持 Word、PDF 等常见格式接入，完成简历内容提取、模块识别、多维度评价、岗位匹配和修改建议生成，并提供可视化报告和导出能力。在此基础上，我们把单份简历分析延伸为学生诊断、教师班级洞察、岗位与简历质量沉淀的就业数据治理闭环。", "caption":"功能完整｜解析可追溯｜评价有依据｜结果可交付"})

    add_heading(doc, "1:15—2:15 学生端：上传与实时分析", 2)
    scene_table(doc, {"time":"1:15—2:15", "visual":"进入“单份分析”。上传准备好的 DOCX 简历，输入目标岗位“数据分析实习生”，点击开始分析。展示 SSE 实时分析流：读取文本、识别板块、命中关键词、质量提示、评分完成。", "voice":"学生进入单份分析页面，上传简历并填写目标岗位。系统首先完成正文提取、分节识别和结构化抽取，识别教育背景、实习经历、项目经验、技能证书等核心模块。分析过程不是一个黑盒等待，而是通过实时事件展示当前正在完成的工作：正在读取哪些内容，识别到哪些板块，发现哪些岗位关键词，以及是否存在文本可读性问题。", "caption":"上传 → 提取 → 分节 → 识别 → 评价\n实时过程可见，异常状态可追踪",})

    add_heading(doc, "2:15—3:05 解析与可信度：结果不能只看一个分数", 2)
    scene_table(doc, {"time":"2:15—3:05", "visual":"进入简历详情，依次点击“链路、可读、可信”状态区域；展示六维评分雷达、质量告警、证据覆盖和低信噪比提示。必要时插入扫描 PDF OCR 前后对比。", "voice":"我们特别区分三个层次。第一，链路完成，说明文件被接入并完成分析；第二，文本可读，说明机器真正读到了足够正文；第三，分析可信，说明评分和建议有足够证据支撑。扫描 PDF 可能分析流程成功，但原生文本为空，因此系统不会把“成功返回”包装成“解析准确”，而是提示需要 OCR 或人工复核。这样的分层，让学生知道结果能不能直接使用，也让教师知道哪些案例需要进一步介入。", "caption":"链路完成 ≠ 文本可读 ≠ 分析可信\n不确定时提示人工复核，不虚高分"})

    add_heading(doc, "3:05—3:55 六维评价：从问题识别到证据定位", 2)
    scene_table(doc, {"time":"3:05—3:55", "visual":"展示六维评分：完整性、经历、语言、格式、亮点、岗位匹配。点击一个低分维度，展示具体问题、证据片段和建议。", "voice":"在评价环节，系统从内容完整性、经历质量、语言表达、格式规范、亮点突出度和岗位匹配六个维度进行分析。这里的重点不是给出一个漂亮的总分，而是把总分拆成可以行动的问题。例如，项目经历写了“参与系统开发”，但没有说明本人负责什么、使用什么工具、取得什么结果，系统会把它识别为证据不足，并给出补充方向，而不是凭空补写成果。", "caption":"六维评分只是入口\n证据片段和可执行建议才是结果"})

    add_heading(doc, "3:55—4:55 岗位匹配：让简历适配具体岗位", 2)
    scene_table(doc, {"time":"3:55—4:55", "visual":"进入岗位匹配页。展示岗位画像、匹配分、命中关键词、缺失关键词、证据片段、学历/经验约束和 Top5 推荐岗位。点击命中词，展示正文高亮。", "voice":"同一份简历，面对不同岗位，评价重点不能一样。系统根据目标岗位和岗位描述建立岗位画像，结合语义匹配与规则核验，展示命中的技能、缺失的要求和对应证据片段。对于学历等硬性要求，规则层负责判断；证据不足时返回未知并提示核验，不强行下结论。这样，学生看到的不只是“匹配度多少”，而是还需要补充什么、哪些经历可以前置，以及为什么得到这个结果。", "caption":"语义理解：判断匹配关系\n规则护航：校验硬约束\n证据解释：说明为什么"})

    add_heading(doc, "4:55—5:55 优化稿交付：建议真正落到文档", 2)
    scene_table(doc, {"time":"4:55—5:55", "visual":"进入“诊断与优化稿”。展示初稿与优化稿 Diff，滚动查看修改项，点击下载 DOCX。打开生成的 Word，展示完整结构和“待补充”标记。", "voice":"我们的交付不是停在建议列表。系统以初稿为基础生成可下载的优化稿，并通过 Diff 清楚展示改了什么。对于原简历中没有证据支持的内容，系统使用“待补充”标记，不编造学校、经历、技能、量化成果或任职结果。学生可以直接拿到一份可继续修改的 Word 文档，教师也能快速定位需要人工指导的部分。", "caption":"从“告诉你怎么改”到“交付一份可继续使用的优化稿”\n不编造经历，不替代人工确认"})

    add_heading(doc, "5:55—6:35 版本与训练：看见改进过程", 2)
    scene_table(doc, {"time":"5:55—6:35", "visual":"上传第二版简历或打开历史版本。展示六维 Δ 分、版本对比和报告中心。切换到模拟面试，展示根据岗位缺口生成的追问。", "voice":"简历优化不是一次性动作。系统保留历史版本，展示每一版在六个维度上的变化，帮助学生看到修改是否真的有效。对于岗位缺口，系统还可以生成针对性模拟面试问题，把简历修改与面试准备连接起来，形成“诊断—修改—验证—训练”的连续过程。", "caption":"版本时光机：记录每一次改进\n岗位缺口也可以转化为面试训练"})

    add_heading(doc, "6:35—7:25 教师端：从个体简历到班级指导", 2)
    scene_table(doc, {"time":"6:35—7:25", "visual":"切换教师账号，展示班级看板、专业/年级统计、常见短板和一键成课模板。注意不展示简历正文、姓名、电话、邮箱。", "voice":"对教师而言，平台的价值不只是少看几份简历，更是把个体问题汇总成班级指导依据。教师端展示班级、专业和年级层面的聚合统计，例如项目经历缺少量化表达、技能缺少证据支撑、求职意向不清等，并据此生成专题指导模板。教师看到的是必要的统计信息，而不是学生简历正文，从而兼顾指导效率与隐私保护。", "caption":"学生问题聚合为教师课程抓手\n教师看统计，不看不必要的简历正文"})

    add_heading(doc, "7:25—8:05 技术架构：三擎协同而不是单一模型", 2)
    scene_table(doc, {"time":"7:25—8:05", "visual":"展示三擎架构动画或简洁流程图：上传 → 语义理解 → 证据护航 → 生成交付。画面旁边同步出现本地规则、岗位库、技能图谱和报告模块。", "voice":"简析智评采用三擎协同架构。语义理解引擎负责理解简历和岗位之间的关系；证据护航引擎负责硬约束、关键词核验、低信噪比提示和结果解释；生成交付引擎负责把诊断转化为优化稿、报告和训练建议。三者协同的结果，是既有智能分析，也有证据边界和可交付产物。即使没有云端大模型，系统仍可通过本地规则和模板回退完成核心流程。", "caption":"语义理解｜证据护航｜生成交付\n可解释、可回退、可交付"})

    add_heading(doc, "8:05—8:30 数据安全与结尾", 2)
    scene_table(doc, {"time":"8:05—8:30", "visual":"展示系统安全说明、角色权限和删除历史操作；最后回到项目 Logo、三擎架构和一句话结论。", "voice":"在数据安全方面，原始简历默认在本地处理，真实简历不进入代码仓库、训练集或对外分享包；教师端只展示聚合统计，删除历史时同步清理相关文件。简析智评不追求用一个未经验证的数字证明一切，而是把能力、证据和边界说清楚。简析智评，先匹配、再护航、后交付，让一份简历成为学生成长和高校就业指导可以持续利用的数据资产。", "caption":"简析智评\n先匹配、再护航、后交付"})

    add_heading(doc, "四、指标与答辩口径：视频中如何说才准确", 1)
    add_callout(doc, "必须分层", "成功率只证明链路能跑通；可读率只说明机器是否读到正文；板块 F1 才能在有人工标签的样本上谈识别可信度。三者不能合并成一个“解析准确率”。", fill="FFF7E6", color=GOLD)
    add_table(doc, ["层级", "当前冻结结果", "视频可说", "视频不要说"], [
        ["L1 链路", "59 份分析成功率 100%", "系统可完成接入、分析和交付", "解析准确率 100%"],
        ["L2 可读", "无 OCR 原生可读率约 55.9%；PDF OCR 后可读率上升", "扫描件需要 OCR，系统能提示边界", "OCR 后所有字段都准确"],
        ["L3 可信", "15 条真实脱敏、第三方裁决样本，板块 micro F1 0.9785", "在限定样本和板块口径下有识别证据", "字段级准确率、全库泛化准确率"],
        ["探索附录", "61 条弱标注匹配实验", "如被追问，说明是探索性结果", "主视频展示 Spearman、融合提升或微调泛化"],
    ], [1100, 2300, 3000, 2960])
    add_para(doc, "推荐配音句： “我们的结果分为链路、可读和可信三个层次。链路成功不等于解析准确；真实样本的板块 F1 也明确限定了数据、标签和评测口径。对于低质量输入，系统选择告警和人工复核，而不是把不确定结果包装成高分。”", bold_prefix="推荐配音句：")

    add_heading(doc, "五、拍摄前准备清单", 1)
    add_table(doc, ["类别", "拍摄前必须准备", "负责人检查"], [
        ["演示数据", "1 份清晰 DOCX；1 份复杂/扫描 PDF 作为边界样例；1 份含项目经历但证据不足的简历", "姓名、电话、邮箱、学校等均已脱敏"],
        ["岗位输入", "数据分析实习生岗位名称或固定 JD；确保岗位关键词与示例简历有命中和缺口", "不要临时输入无法解释的岗位"],
        ["演示路径", "单份分析 → 实时流 → 分层可信度 → 六维评分 → 岗位匹配 → Diff → 下载报告 → 教师端", "完整走通至少 3 次"],
        ["环境", "浏览器、后端、前端、模型/离线回退、报告导出目录", "提前关闭无关窗口和通知"],
        ["隐私", "使用脱敏文件；检查录屏中没有真实姓名、电话、邮箱、身份证号和 API Key", "录屏前后各检查一次"],
        ["备份", "录制一条无配音备用视频；准备截图版 PPT 作为网络或现场故障备份", "备用材料与当前版本一致"],
    ], [1800, 5700, 1860])

    add_heading(doc, "六、精简版 3 分钟剪辑方案", 1)
    add_para(doc, "如果组委会要求短视频，可保留以下六段，旁白不要重新发明口径，直接从正式脚本中截取：")
    add_table(doc, ["时长", "保留内容", "画面重点"], [
        ["0:00—0:25", "片头与问题", "学生求职痛点 + 项目首页"],
        ["0:25—1:00", "赛题回应", "四项评分点 + 三端闭环"],
        ["1:00—1:45", "学生端分析", "上传、实时流、六维评分、可信度分层"],
        ["1:45—2:15", "岗位匹配", "命中/缺失、硬约束、证据片段"],
        ["2:15—2:40", "优化稿交付", "Diff、待补充、不编造、DOCX 下载"],
        ["2:40—3:00", "教师端与结尾", "班级聚合、隐私边界、三擎结论"],
    ], [1300, 3800, 4060])

    add_heading(doc, "七、拍摄禁区与最终检查", 1)
    add_bullets(doc, [
        "不要把 59 份分析成功率 100% 说成解析准确率 100%。",
        "不要把 15 条脱敏样本的板块 F1 说成字段抽取准确率或全库泛化结果。",
        "不要在主视频中展示 61 条弱标注集上的微调、融合权重或 Spearman 提升。",
        "不要展示真实姓名、电话、邮箱、身份证号、学校等敏感信息。",
        "不要把 DeepSeek 说成项目唯一核心；应说明无 Key 时核心流程可以离线回退。",
        "不要演示尚未稳定验证的新功能；视频版本应与最终冻结版本一致。",
    ])
    add_callout(doc, "结尾口径", "我们不把智能分析包装成不可质疑的自动结论，而是用语义理解提高匹配效率，用规则和证据控制风险，用生成交付把建议落实到可继续使用的优化稿，最终服务学生成长和高校就业指导。", fill="E8EEF5")

    add_heading(doc, "附录：视频字幕短句库", 1)
    add_table(doc, ["位置", "建议字幕"], [
        ["片头", "简析智评｜高校就业数据治理闭环"],
        ["上传", "支持 Word / PDF 等常见简历文件"],
        ["解析", "分节识别 + 结构化抽取 + OCR 兜底"],
        ["可信度", "链路完成 ≠ 文本可读 ≠ 分析可信"],
        ["评分", "六维评价：完整性、经历、语言、格式、亮点、岗位匹配"],
        ["匹配", "命中什么、缺什么、为什么"],
        ["优化", "基于初稿生成优化稿，不编造经历"],
        ["教师端", "聚合短板，不展示不必要的简历正文"],
        ["结尾", "先匹配、再护航、后交付"],
    ], [1800, 7560])

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
