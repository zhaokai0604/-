from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1600
HEIGHT = 900
BG = (247, 249, 252)
BLUE = (34, 91, 170)
DARK = (20, 45, 90)
LIGHT = (232, 239, 250)
LIGHTER = (244, 247, 252)
GRAY = (92, 104, 120)
LINE = (160, 176, 198)
SUCCESS = (52, 130, 91)
GOLD = (184, 132, 56)
RED = (164, 74, 74)


def ensure_figure_assets(asset_dir: Path, font_path: Path) -> dict[str, Path]:
    asset_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "图1-1": asset_dir / "fig_1_1_roles.png",
        "图1-2": asset_dir / "fig_1_2_value_path.png",
        "图1-3": asset_dir / "fig_1_3_research_map.png",
        "图2-1": asset_dir / "fig_2_1_architecture.png",
        "图2-2": asset_dir / "fig_2_2_business_flow.png",
        "图3-1": asset_dir / "fig_3_1_six_dimensions.png",
        "图3-2": asset_dir / "fig_3_2_demo_flow.png",
        "图3-3": asset_dir / "fig_3_3_security_boundary.png",
        "图3-4": asset_dir / "fig_3_4_task_pipeline.png",
        "图3-5": asset_dir / "fig_3_5_credibility.png",
        "图4-1": asset_dir / "fig_4_1_value_path.png",
        "图4-2": asset_dir / "fig_4_2_showcase_flow.png",
        "图5-1": asset_dir / "fig_5_1_roadmap.png",
        "图5-2": asset_dir / "fig_5_2_credibility.png",
        "图A-1": asset_dir / "fig_a_1_testing_structure.png",
        "图A-2": asset_dir / "fig_a_2_ci_flow.png",
    }
    builders: dict[str, Callable[[Path, Path], None]] = {
        "图1-1": build_roles_collaboration,
        "图1-2": build_value_path,
        "图1-3": build_research_mapping,
        "图2-1": build_system_architecture,
        "图2-2": build_business_flow,
        "图3-1": build_six_dimensions,
        "图3-2": build_demo_flow,
        "图3-3": build_security_boundary,
        "图3-4": build_task_pipeline,
        "图3-5": build_credibility_sources,
        "图4-1": build_value_path,
        "图4-2": build_showcase_flow,
        "图5-1": build_roadmap,
        "图5-2": build_credibility_sources,
        "图A-1": build_testing_structure,
        "图A-2": build_ci_flow,
    }
    for code, path in mapping.items():
        builders[code](path, font_path)
    return mapping


def _font(font_path: Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(font_path), size=size)
    except Exception:
        return ImageFont.load_default()


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 28, WIDTH - 28, HEIGHT - 28), radius=28, outline=LINE, width=3, fill=BG)
    return image, draw


def _wrap(text: str, limit: int) -> str:
    lines: list[str] = []
    current = ""
    for ch in text:
        current += ch
        if len(current) >= limit:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return "\n".join(lines)


def _header(draw: ImageDraw.ImageDraw, font_path: Path, title: str, subtitle: str = "") -> None:
    draw.text((80, 56), title, font=_font(font_path, 38), fill=DARK)
    if subtitle:
        draw.text((80, 108), subtitle, font=_font(font_path, 18), fill=GRAY)
    draw.line((80, 142, WIDTH - 80, 142), fill=BLUE, width=4)


def _box(
    draw: ImageDraw.ImageDraw,
    font_path: Path,
    xy: tuple[int, int, int, int],
    title: str,
    body: str = "",
    *,
    fill: tuple[int, int, int] = LIGHT,
    border: tuple[int, int, int] = BLUE,
    title_fill: tuple[int, int, int] = DARK,
    body_fill: tuple[int, int, int] = GRAY,
    title_size: int = 24,
    body_size: int = 18,
    wrap_limit: int = 16,
) -> None:
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=26, outline=border, width=4, fill=fill)
    draw.text((x1 + 20, y1 + 18), title, font=_font(font_path, title_size), fill=title_fill)
    if body:
        draw.multiline_text(
            (x1 + 20, y1 + 62),
            _wrap(body, wrap_limit),
            font=_font(font_path, body_size),
            fill=body_fill,
            spacing=8,
        )


def _center_box(
    draw: ImageDraw.ImageDraw,
    font_path: Path,
    xy: tuple[int, int, int, int],
    title: str,
    body: str = "",
    *,
    fill: tuple[int, int, int] = LIGHTER,
    border: tuple[int, int, int] = BLUE,
    title_size: int = 24,
    body_size: int = 18,
    wrap_limit: int = 18,
) -> None:
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=26, outline=border, width=4, fill=fill)
    title_font = _font(font_path, title_size)
    body_font = _font(font_path, body_size)
    title_bbox = draw.multiline_textbbox((0, 0), title, font=title_font, spacing=8)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text((x1 + (x2 - x1 - title_w) / 2, y1 + 18), title, font=title_font, fill=DARK)
    if body:
        wrapped = _wrap(body, wrap_limit)
        body_bbox = draw.multiline_textbbox((0, 0), wrapped, font=body_font, spacing=8)
        body_w = body_bbox[2] - body_bbox[0]
        draw.multiline_text(
            (x1 + (x2 - x1 - body_w) / 2, y1 + 70),
            wrapped,
            font=body_font,
            fill=GRAY,
            spacing=8,
            align="center",
        )


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], *, color: tuple[int, int, int] = BLUE, width: int = 6) -> None:
    draw.line((start, end), fill=color, width=width)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) >= abs(ey - sy):
        if ex >= sx:
            pts = [(ex, ey), (ex - 18, ey - 10), (ex - 18, ey + 10)]
        else:
            pts = [(ex, ey), (ex + 18, ey - 10), (ex + 18, ey + 10)]
    else:
        if ey >= sy:
            pts = [(ex, ey), (ex - 10, ey - 18), (ex + 10, ey - 18)]
        else:
            pts = [(ex, ey), (ex - 10, ey + 18), (ex + 10, ey + 18)]
    draw.polygon(pts, fill=color)


def build_roles_collaboration(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "三角色协同关系图", "学生端聚焦个体诊断，教师端聚焦群体指导，管理端聚焦治理与运行")
    _center_box(draw, font_path, (540, 300, 1060, 560), "简历评价与分析平台", "上传、解析、评价、匹配、建议、报告、沉淀")
    _box(draw, font_path, (90, 250, 420, 500), "学生端", "上传单份或批量简历\n查看评分、岗位匹配与建议\n下载 Word/PDF 报告", fill=(236, 244, 252), wrap_limit=12)
    _box(draw, font_path, (1180, 250, 1510, 500), "教师端", "查看班级统计、共性问题\n回看学生记录元数据\n导出群体分析结果", fill=(236, 244, 252), wrap_limit=12)
    _box(draw, font_path, (540, 640, 1060, 820), "管理端", "用户角色、AI 配置、评分模板、审计日志、存储清理", fill=(236, 244, 252), wrap_limit=20)
    _arrow(draw, (420, 380), (540, 380))
    _arrow(draw, (1180, 380), (1060, 380))
    _arrow(draw, (800, 640), (800, 560))
    image.save(path)


def build_value_path(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "平台应用效果路径图", "从个体求职准备到群体指导再到学校就业服务资产沉淀")
    bands = [
        ((80, 200, 1520, 340), "学生层", "缩短修改周期 | 围绕目标岗位优化 | 形成报告化成果"),
        ((80, 390, 1520, 530), "教师层", "识别班级共性问题 | 快速组织专题辅导 | 提升有限时间利用率"),
        ((80, 580, 1520, 720), "学校层", "形成留痕化、标准化、可复盘的就业服务数字化能力"),
    ]
    for xy, title, body in bands:
        _box(draw, font_path, xy, title, body, fill=LIGHTER, wrap_limit=28, title_size=26, body_size=20)
    _arrow(draw, (800, 340), (800, 390))
    _arrow(draw, (800, 530), (800, 580))
    image.save(path)


def build_research_mapping(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "科研支撑到系统实现的映射图", "研究方向不是停留在综述层，而是服务于当前平台路线选择")
    cols = [
        ((90, 220, 450, 760), "研究支撑", "文档解析\n岗位匹配\n可解释推荐\n任务编排\n报告生成"),
        ((620, 220, 980, 760), "方法落点", "结构化板块识别\nmust/nice 关键词体系\n证据片段抽取\n规则主链 + AI 增强\nWord/PDF 输出"),
        ((1150, 220, 1510, 760), "系统实现", "parser.py\ndocument_ingest.py\nmatch_engine.py\nsuggestion_engine.py\nreport.py"),
    ]
    for xy, title, body in cols:
        _center_box(draw, font_path, xy, title, body, wrap_limit=12, title_size=28, body_size=22)
    _arrow(draw, (450, 490), (620, 490))
    _arrow(draw, (980, 490), (1150, 490))
    image.save(path)


def build_system_architecture(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "系统总体架构图", "前后端分离 + 服务层 + 任务层 + 数据层的高校就业指导平台")
    _center_box(draw, font_path, (470, 170, 1130, 270), "浏览器端", "学生工作台 | 教师看板 | 管理后台", title_size=28, body_size=22, wrap_limit=22)
    _center_box(draw, font_path, (380, 320, 1220, 430), "API 层（FastAPI）", "认证、分析、历史、任务、岗位、教师、管理接口", title_size=28, body_size=22, wrap_limit=26)
    _box(draw, font_path, (120, 500, 470, 770), "分析服务层", "document_ingest\nparser\nscore_engine\nmatch_engine\nsuggestion_engine", wrap_limit=12, body_size=20)
    _box(draw, font_path, (625, 500, 975, 770), "增强与任务层", "resume_rewriter\ninterview_engine\nRedis + Celery\nbatch_service", wrap_limit=13, body_size=20, fill=(236, 244, 252))
    _box(draw, font_path, (1130, 500, 1480, 770), "数据与产物层", "MySQL\n上传文件\n报告目录\n日志与审计", wrap_limit=12, body_size=20, fill=(236, 244, 252))
    _arrow(draw, (800, 270), (800, 320))
    _arrow(draw, (800, 430), (295, 500))
    _arrow(draw, (800, 430), (800, 500))
    _arrow(draw, (800, 430), (1305, 500))
    image.save(path)


def build_business_flow(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "核心业务流程图", "平台不是单点打分工具，而是完整链路型简历服务系统")
    steps = [
        "上传简历",
        "格式校验",
        "结构化解析",
        "六维评价",
        "岗位匹配",
        "建议生成",
        "报告沉淀",
    ]
    left = 70
    top = 360
    width = 190
    gap = 25
    for idx, step in enumerate(steps):
        x1 = left + idx * (width + gap)
        x2 = x1 + width
        _center_box(draw, font_path, (x1, top, x2, 530), f"{idx+1}. {step}", "", title_size=24, body_size=18)
        if idx < len(steps) - 1:
            _arrow(draw, (x2, 445), (x2 + gap, 445))
    draw.text((88, 585), "结果同步写入历史记录、任务中心和报告中心，形成可回看的平台资产", font=_font(font_path, 24), fill=GRAY)
    image.save(path)


def build_six_dimensions(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "六维评价模型图", "以可解释和可执行为导向的量化评价框架")
    _center_box(draw, font_path, (620, 320, 980, 580), "六维评价", "总评分 + 分项得分 + 证据 + 建议", title_size=34, body_size=22, wrap_limit=14)
    items = [
        ((110, 200, 490, 330), "内容完整性", "看核心板块是否齐全"),
        ((110, 390, 490, 520), "经历相关性", "看经历是否支撑岗位能力"),
        ((110, 580, 490, 710), "语言专业性", "看表达是否专业、简洁"),
        ((1110, 200, 1490, 330), "格式规范性", "看结构、日期、联系方式等规范度"),
        ((1110, 390, 1490, 520), "亮点量化程度", "看是否有数据、比例、成果结果"),
        ((1110, 580, 1490, 710), "岗位语义匹配", "看关键词覆盖、缺失要素与证据"),
    ]
    for xy, title, body in items:
        _box(draw, font_path, xy, title, body, fill=LIGHTER, wrap_limit=18, title_size=24, body_size=18)
    for start, end in [
        ((490, 265), (620, 350)),
        ((490, 455), (620, 450)),
        ((490, 645), (620, 550)),
        ((1110, 265), (980, 350)),
        ((1110, 455), (980, 450)),
        ((1110, 645), (980, 550)),
    ]:
        _arrow(draw, start, end)
    image.save(path)


def build_demo_flow(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "比赛演示流程图", "按评委理解路径组织功能展示顺序")
    draw.line((140, 440, 1460, 440), fill=BLUE, width=8)
    nodes = [
        (160, "登录/游客"),
        (410, "上传简历"),
        (660, "查看评分"),
        (910, "查看匹配"),
        (1160, "下载报告"),
        (1410, "教师/管理端"),
    ]
    for x, label in nodes:
        draw.ellipse((x - 42, 398, x + 42, 482), fill=LIGHT, outline=BLUE, width=4)
        idx = nodes.index((x, label)) + 1
        num_font = _font(font_path, 24)
        draw.text((x - 10, 416), str(idx), font=num_font, fill=DARK)
        draw.multiline_text((x - 74, 500), _wrap(label, 6), font=_font(font_path, 20), fill=GRAY, align="center")
    image.save(path)


def build_security_boundary(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "数据流与安全边界图", "规则主链默认本地闭环，AI 增强仅在开启且配置可用时触发")
    _box(draw, font_path, (90, 210, 700, 730), "本地闭环区", "上传文件\nDOCX/PDF/ZIP 校验\n文本提取与结构化解析\n六维评分与岗位匹配\nWord/PDF 报告生成\n历史记录与文件清理", fill=(238, 247, 242), border=SUCCESS, wrap_limit=14)
    _box(draw, font_path, (900, 260, 1510, 680), "可选外部 AI 区", "仅在配置 DEEPSEEK_API_KEY 且用户开启时调用\n用于增强诊断表达、改写预览和面试准备\n异常时自动回退为 offline_fallback", fill=(252, 244, 236), border=GOLD, wrap_limit=18)
    _arrow(draw, (700, 470), (900, 470))
    draw.text((760, 430), "可选增强调用", font=_font(font_path, 20), fill=GOLD)
    draw.text((760, 500), "默认可关闭", font=_font(font_path, 20), fill=GRAY)
    image.save(path)


def build_task_pipeline(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "任务处理流程图", "单份分析、批量分析和报告生成围绕统一任务主线组织")
    _center_box(draw, font_path, (70, 320, 310, 510), "任务创建", "单份上传\nZIP 批量上传", title_size=26, body_size=20)
    _center_box(draw, font_path, (390, 240, 690, 430), "解析与评分", "document_ingest\nparser\nscore_engine", title_size=26, body_size=20)
    _center_box(draw, font_path, (390, 490, 690, 680), "异步编排", "Redis + Celery\n批量任务状态追踪", title_size=26, body_size=20)
    _center_box(draw, font_path, (820, 240, 1120, 430), "匹配与建议", "match_engine\nsuggestion_engine\nrewrite_preview", title_size=26, body_size=20)
    _center_box(draw, font_path, (820, 490, 1120, 680), "报告产物", "Word 即时生成\nPDF 按需生成", title_size=26, body_size=20)
    _center_box(draw, font_path, (1240, 320, 1520, 510), "历史沉淀", "任务中心\n报告中心\n教师统计", title_size=26, body_size=20)
    for start, end in [
        ((310, 415), (390, 335)),
        ((310, 415), (390, 585)),
        ((690, 335), (820, 335)),
        ((690, 585), (820, 585)),
        ((1120, 335), (1240, 415)),
        ((1120, 585), (1240, 415)),
    ]:
        _arrow(draw, start, end)
    image.save(path)


def build_credibility_sources(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "项目可信性来源结构图", "可信度来自政策背景、代码实现、测试构建、部署材料和治理边界的共同支撑")
    pillars = [
        (110, 360, 320, 760, "政策背景", "2025-11-20\n2025-04-08\n2026-04-23\n2026-06-08"),
        (390, 300, 600, 760, "代码实现", "14 个 API 模块\n26 个服务模块\n58 条路由"),
        (670, 240, 930, 760, "测试构建", "25 个测试文件\n107 个测试函数\n前端 build 通过"),
        (1000, 300, 1210, 760, "部署材料", "Docker Compose\nNginx 配置\n健康检查"),
        (1280, 360, 1490, 760, "治理边界", "用户隔离\nAI 开关\n文件清理"),
    ]
    for x1, y1, x2, y2, title, body in pillars:
        _center_box(draw, font_path, (x1, y1, x2, y2), title, body, title_size=26, body_size=20, wrap_limit=10)
    image.save(path)


def build_showcase_flow(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "比赛展示流程图", "答辩路线围绕痛点、方案、技术、验证和价值逐步展开")
    blocks = [
        ("赛题痛点", "毕业生规模增长、人工指导效率不足"),
        ("平台闭环", "上传、解析、评价、匹配、建议、导出、沉淀"),
        ("关键技术", "结构化解析、六维评价、证据匹配、离线回退"),
        ("工程证明", "107 项测试通过、前端构建通过、部署材料齐全"),
        ("应用价值", "学生、教师、学校三层价值落点"),
    ]
    y = 180
    for idx, (title, body) in enumerate(blocks, 1):
        _center_box(draw, font_path, (330, y, 1270, y + 105), f"{idx}. {title}", body, title_size=28, body_size=20, wrap_limit=28)
        if idx < len(blocks):
            _arrow(draw, (800, y + 105), (800, y + 150))
        y += 150
    image.save(path)


def build_roadmap(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "当前能力与未来扩展路线图", "在现有平台骨架上沿着更强解析、更强匹配、更强治理持续迭代")
    _center_box(draw, font_path, (90, 220, 460, 720), "当前能力", "多格式接入\n结构化解析\n六维评价\n岗位匹配\n报告导出\n教师/管理端", title_size=28, body_size=22, wrap_limit=10)
    _center_box(draw, font_path, (610, 220, 980, 720), "中期优化", "复杂版式解析\n更强 OCR 清洗\n语义检索与重排\n更深层班级统计", title_size=28, body_size=22, wrap_limit=11)
    _center_box(draw, font_path, (1130, 220, 1500, 720), "长期拓展", "职业规划\n面试训练\n校企协同\n就业数据大屏\n持续治理能力", title_size=28, body_size=22, wrap_limit=11)
    _arrow(draw, (460, 470), (610, 470))
    _arrow(draw, (980, 470), (1130, 470))
    image.save(path)


def build_testing_structure(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "测试验证支撑结构图", "以自动化测试、构建验证和部署检查共同支撑工程可信性")
    _center_box(draw, font_path, (610, 110, 990, 220), "验证目标", "证明系统真实可运行、可回归、可展示", title_size=30, body_size=20, wrap_limit=18)
    _box(draw, font_path, (90, 300, 470, 620), "后端测试", "25 个测试文件\n107 个测试函数\n覆盖解析、流水线、批量、权限、教师端等", fill=(236, 244, 252), wrap_limit=14)
    _box(draw, font_path, (610, 300, 990, 620), "前端构建", "npm run build\n2161 modules transformed\n生成 dist 产物", fill=(236, 244, 252), wrap_limit=14)
    _box(draw, font_path, (1130, 300, 1510, 620), "部署检查", "Docker Compose\n/api/health\n数据目录与报告目录检查", fill=(236, 244, 252), wrap_limit=14)
    _arrow(draw, (800, 220), (280, 300))
    _arrow(draw, (800, 220), (800, 300))
    _arrow(draw, (800, 220), (1320, 300))
    image.save(path)


def build_ci_flow(path: Path, font_path: Path) -> None:
    image, draw = _canvas()
    _header(draw, font_path, "CI 流程示意图", "仓库当前采用单个 ci.yml 同时执行后端测试和前端构建")
    steps = [
        ("触发条件", "push 到 main/master\n或 pull request"),
        ("后端 Job", "Python 3.12\n安装 requirements\npytest tests/ -q"),
        ("前端 Job", "Node 20\nnpm ci\nnpm run build"),
        ("结果输出", "回传测试与构建结果\n为提交和答辩提供证明"),
    ]
    x = 70
    for idx, (title, body) in enumerate(steps):
        _center_box(draw, font_path, (x, 320, x + 320, 580), title, body, title_size=28, body_size=20, wrap_limit=12)
        if idx < len(steps) - 1:
            _arrow(draw, (x + 320, 450), (x + 380, 450))
        x += 380
    image.save(path)
