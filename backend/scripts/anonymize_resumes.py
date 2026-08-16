"""真实简历脱敏清洗器（字段级、偏保守、不可逆占位）。

输入:  data/raw_real_resumes/     （原始 docx/pdf/txt，勿提交 git）
输出:  data/anonymized_real_resumes/
  - *.txt                 始终输出脱敏纯文本（评测/分拣主用）
  - *.docx                尽量就地替换段落/表格文字后另存（结构保留尽力而为）
  - anonymize_report.json 替换统计与告警
  - manifest.json         原文件 → 输出映射（不含原文）

用法:
  cd backend
  .\\.venv\\Scripts\\python.exe scripts\\anonymize_resumes.py
  .\\.venv\\Scripts\\python.exe scripts\\anonymize_resumes.py --input ..\\data\\raw_real_resumes --dry-run

安全红线:
  - 不调用大模型
  - 不写入 match 训练标签
  - 原始目录应被 .gitignore；请勿把 raw 打进参赛附件
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "anonymize-resume-secret")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _resume_corpus_common import (  # noqa: E402
    default_anon_dir,
    default_raw_dir,
    ensure_dir,
    extract_text,
    iter_resume_files,
    safe_stem,
    write_json,
)

# ---------- 占位符 ----------
PHONE = "【手机号】"
EMAIL = "【邮箱】"
IDCARD = "【证件号】"
WECHAT = "【微信号】"
QQ = "【QQ号】"
NAME = "【姓名】"
SCHOOL = "【高校】"
COMPANY = "【机构】"
ADDRESS = "【地址】"
URL = "【链接】"
GITHUB = "【账号主页】"

# 绝不作为「姓名」替换的词（专业/技能/常见板块/动词短语碎片）
NAME_BLOCKLIST = frozenset(
    {
        "教育背景",
        "实习经历",
        "工作经历",
        "项目经历",
        "专业技能",
        "自我评价",
        "求职意向",
        "基本信息",
        "个人信息",
        "联系方式",
        "获奖情况",
        "校园经历",
        "社会实践",
        "主修课程",
        "数据分析",
        "数据挖掘",
        "数据运营",
        "软件工程",
        "计算机",
        "人工智能",
        "深度学习",
        "机器学习",
        "前端开发",
        "后端开发",
        "全栈开发",
        "产品经理",
        "产品设计",
        "视觉设计",
        "平面设计",
        "新媒体",
        "内容运营",
        "用户运营",
        "活动运营",
        "人力资源",
        "电子商务",
        "市场营销",
        "财务管理",
        "会计学",
        "法学",
        "英语",
        "日语",
        "本科",
        "专科",
        "硕士",
        "博士",
        "研究生",
        "应届生",
        "在校生",
        "实习生",
        "负责人",
        "工程师",
        "设计师",
        "分析师",
        "运营官",
        "程序员",
        "开发者",
        "团队协作",
        "沟通能力",
        "学习能力",
        "抗压能力",
        "责任心",
        "吃苦耐劳",
        "乐观开朗",
        "认真负责",
        "工作认真",
        "熟悉",
        "掌握",
        "了解",
        "负责",
        "参与",
        "完成",
        "协助",
        "优化",
        "维护",
        "设计",
        "开发",
        "测试",
        "部署",
        "简历",
        "个人",
        "目前",
        "现居",
        "期望",
        "意向",
        "目标",
        "岗位",
        "职位",
        "公司",
        "集团",
        "有限",
        "股份",
        "北京",
        "上海",
        "广州",
        "深圳",
        "杭州",
        "成都",
        "武汉",
        "西安",
        "南京",
        "苏州",
        "天津",
        "重庆",
        "长沙",
        "郑州",
        "青岛",
        "大连",
        "厦门",
        "合肥",
        "福州",
        "济南",
        "哈尔滨",
        "沈阳",
        "昆明",
        "南昌",
        "石家庄",
        "太原",
        "南宁",
        "贵阳",
        "海口",
        "兰州",
        "银川",
        "西宁",
        "呼和浩特",
        "乌鲁木齐",
        "拉萨",
    }
)

MAJOR_HINT = re.compile(
    r"(管理|工程|科学|技术|经济|法学|医学|文学|理学|工学|农学|艺术|计算机|软件|电子|"
    r"机械|土木|新闻|广告|设计|英语|数学|物理|化学|生物|护理|教育|营销|贸易|物流|"
    r"心理|统计|通信|自动化|建筑|环境|材料|食品|药学|会计|金融|人力|数据|智能|媒体|"
    r"传播|编辑|财务|网络|信息|国际|商务|公共)"
)

PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
IDCARD_RE = re.compile(r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")
QQ_RE = re.compile(r"(?:QQ|qq)\s*[:：]?\s*([1-9]\d{4,11})")
WECHAT_RE = re.compile(r"(?:微信|WeChat|wechat|WX|wx)\s*[:：]?\s*([A-Za-z][\w\-]{2,30})")
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
GITHUB_RE = re.compile(r"(?:github\.com|gitee\.com)/[A-Za-z0-9_.\-]+", re.I)
SCHOOL_RE = re.compile(
    r"[\u4e00-\u9fa5A-Za-z]{2,20}?(?:大学|学院|职业技术学院|职业技术大学|研究院|高等专科学校)[\u4e00-\u9fa5]{0,8}"
)
COMPANY_RE = re.compile(
    r"[\u4e00-\u9fa5A-Za-z0-9（）()]{2,24}(?:有限公司|股份有限公司|集团有限公司|科技公司|网络公司|传媒公司|文化公司)"
)
ADDRESS_RE = re.compile(
    r"(?:现居|现居地|居住地|所在地|通讯地址|家庭住址|地址)\s*[:：]?\s*([\u4e00-\u9fa5A-Za-z0-9\-号室层弄区市县镇乡街道路巷村]{4,40})"
)
NAME_LABEL_RE = re.compile(
    r"(?:姓名|名字|Name)\s*[:：]\s*([·\u4e00-\u9fa5]{2,4})",
    re.I,
)
# 首行像姓名：仅 2-4 汉字/间隔点，且不在黑名单
FIRST_LINE_NAME_RE = re.compile(r"^[\u4e00-\u9fa5]{2,4}(?:·[\u4e00-\u9fa5]{1,3})?$")


def anonymize_text(text: str) -> tuple[str, Counter]:
    """对纯文本做不可逆占位替换，返回 (新文本, 各类替换计数)。"""
    stats: Counter = Counter()
    if not text:
        return "", stats

    def sub(pattern: re.Pattern[str], repl: str, src: str, key: str) -> str:
        def _repl(match: re.Match[str]) -> str:
            stats[key] += 1
            return repl

        return pattern.sub(_repl, src)

    out = text
    out = sub(IDCARD_RE, IDCARD, out, "idcard")
    out = sub(PHONE_RE, PHONE, out, "phone")
    out = sub(EMAIL_RE, EMAIL, out, "email")
    out = sub(URL_RE, URL, out, "url")
    out = sub(GITHUB_RE, GITHUB, out, "github")

    def qq_repl(match: re.Match[str]) -> str:
        stats["qq"] += 1
        return match.group(0).replace(match.group(1), QQ)

    out = QQ_RE.sub(qq_repl, out)

    def wechat_repl(match: re.Match[str]) -> str:
        stats["wechat"] += 1
        return match.group(0).replace(match.group(1), WECHAT)

    out = WECHAT_RE.sub(wechat_repl, out)

    def addr_repl(match: re.Match[str]) -> str:
        stats["address"] += 1
        return match.group(0).replace(match.group(1), ADDRESS)

    out = ADDRESS_RE.sub(addr_repl, out)

    # 学校 / 公司：整段实体替换（避免只吃掉后缀）
    def school_repl(match: re.Match[str]) -> str:
        token = match.group(0)
        # 避免「学院路」「大学生」误伤：必须像机构名
        if "大学生" in token or token in {"大学", "学院", "学校"}:
            return token
        if len(token) < 4:
            return token
        stats["school"] += 1
        return SCHOOL

    out = SCHOOL_RE.sub(school_repl, out)

    def company_repl(match: re.Match[str]) -> str:
        stats["company"] += 1
        return COMPANY

    out = COMPANY_RE.sub(company_repl, out)

    # 姓名：仅标签行 + 首行短专名；禁止全文 2-4 字盲替
    name_hits: set[str] = set()
    for match in NAME_LABEL_RE.finditer(out):
        candidate = match.group(1).strip()
        if _looks_like_person_name(candidate):
            name_hits.add(candidate)

    lines = out.splitlines()
    if lines:
        head = lines[0].strip().split()[0] if lines[0].strip() else ""
        # 「张三 / 数据分析」只取左侧
        head = re.split(r"[|/／]", head, maxsplit=1)[0].strip()
        if FIRST_LINE_NAME_RE.match(head) and _looks_like_person_name(head):
            name_hits.add(head)

    # 按长度降序替换，避免短名嵌在长名里
    for person in sorted(name_hits, key=len, reverse=True):
        pattern = re.compile(rf"(?<![\u4e00-\u9fa5·]){re.escape(person)}(?![\u4e00-\u9fa5·])")
        out, n = pattern.subn(NAME, out)
        stats["name"] += n

    # 二次清理：连续占位挤压
    out = re.sub(r"(【姓名】){2,}", NAME, out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out, stats


def _looks_like_person_name(token: str) -> bool:
    clean = (token or "").strip()
    if not clean or clean in NAME_BLOCKLIST:
        return False
    if MAJOR_HINT.search(clean) and len(clean) >= 3:
        return False
    if re.search(r"(大学|学院|公司|集团|专业|实习|经理|工程师|设计|开发|分析|运营)", clean):
        return False
    if not re.fullmatch(r"[\u4e00-\u9fa5]{2,4}(?:·[\u4e00-\u9fa5]{1,3})?", clean):
        return False
    return True


def anonymize_docx_file(src: Path, dst: Path) -> tuple[Counter, list[str]]:
    """尽量保留 docx 结构，对段落/表格单元格做文本级替换。"""
    warnings: list[str] = []
    stats: Counter = Counter()
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("缺少 python-docx") from exc

    doc = Document(str(src))

    def transform(value: str) -> str:
        new_text, local = anonymize_text(value)
        stats.update(local)
        return new_text

    for paragraph in doc.paragraphs:
        if paragraph.text:
            _set_paragraph_text(paragraph, transform(paragraph.text))
    for table in doc.tables:
        _anonymize_table(table, transform)
    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            if paragraph.text:
                _set_paragraph_text(paragraph, transform(paragraph.text))
        for paragraph in section.footer.paragraphs:
            if paragraph.text:
                _set_paragraph_text(paragraph, transform(paragraph.text))

    # 文本框等可能仍残留；依赖并行输出的 txt 作为权威脱敏正文
    warnings.append("docx 文本框/形状内文字可能无法全部改写；请以同名 .txt 为准做评测")
    ensure_dir(dst.parent)
    doc.save(str(dst))
    return stats, warnings


def _set_paragraph_text(paragraph: Any, text: str) -> None:
    if not paragraph.runs:
        paragraph.text = text
        return
    paragraph.runs[0].text = text
    for run in paragraph.runs[1:]:
        run.text = ""


def _anonymize_table(table: Any, transform) -> None:
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                if paragraph.text:
                    _set_paragraph_text(paragraph, transform(paragraph.text))
            for nested in getattr(cell, "tables", []) or []:
                _anonymize_table(nested, transform)


def process_one(
    path: Path,
    out_dir: Path,
    *,
    dry_run: bool,
    enable_ocr: bool = False,
    ocr_engine: str = "paddleocr",
) -> dict[str, Any]:
    stem = safe_stem(path)
    text, extract_warnings = extract_text(
        path,
        enable_ocr=enable_ocr,
        ocr_engine=ocr_engine,
    )
    anon_text, stats = anonymize_text(text)
    record: dict[str, Any] = {
        "source": path.name,
        "source_path": str(path),
        "stem": stem,
        "suffix": path.suffix.lower(),
        "source_type": path.suffix.lower().lstrip("."),
        "chars_in": len(text),
        "chars_out": len(anon_text),
        "text_length": len(text.strip()),
        "ocr_used": bool(enable_ocr and any("OCR" in item for item in extract_warnings)),
        "extract_status": "ok" if text.strip() else (
            "ocr_failed" if enable_ocr and any("OCR" in item for item in extract_warnings) else
            ("ocr_required" if path.suffix.lower() == ".pdf" else "empty_or_unreadable")
        ),
        "replacements": dict(stats),
        "extract_warnings": extract_warnings,
        "output_txt": f"{stem}.txt",
        "output_docx": None,
        "status": "ok",
        "notes": [],
    }

    if not text.strip():
        record["status"] = "empty_or_unreadable"
        record["notes"].append("未抽到可用正文，已跳过写出（扫描 PDF 请先转文字版）")
        return record

    if dry_run:
        record["notes"].append("dry-run：未写文件")
        return record

    ensure_dir(out_dir)
    txt_path = out_dir / f"{stem}.txt"
    txt_path.write_text(anon_text, encoding="utf-8")

    if path.suffix.lower() == ".docx":
        docx_path = out_dir / f"{stem}.docx"
        try:
            doc_stats, doc_warns = anonymize_docx_file(path, docx_path)
            # 合并统计（docx 路径可能与纯文本重复计数，报告里单独标）
            record["docx_replacements"] = dict(doc_stats)
            record["notes"].extend(doc_warns)
            record["output_docx"] = docx_path.name
        except Exception as exc:  # noqa: BLE001
            record["notes"].append(f"docx 结构保留写出失败，仅保留 txt: {exc}")
    elif path.suffix.lower() == ".pdf":
        record["notes"].append("PDF 不重写二进制版式，仅输出脱敏 txt，避免半脱敏扫描件外泄")

    # 残留启发式检查
    residual = []
    if PHONE_RE.search(anon_text):
        residual.append("phone")
    if EMAIL_RE.search(anon_text):
        residual.append("email")
    if IDCARD_RE.search(anon_text):
        residual.append("idcard")
    if residual:
        record["notes"].append(f"仍可能残留: {','.join(residual)}，请人工抽查")
        record["status"] = "needs_review"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="真实简历脱敏清洗")
    parser.add_argument("--input", type=Path, default=default_raw_dir())
    parser.add_argument("--output", type=Path, default=default_anon_dir())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 个，调试用")
    parser.add_argument("--ocr", action="store_true", help="对文本不足的 PDF 启用本地 PaddleOCR 兜底")
    parser.add_argument("--ocr-engine", default="paddleocr", choices=["paddleocr"])
    args = parser.parse_args()

    ensure_dir(args.input)
    files = iter_resume_files(args.input)
    if args.limit > 0:
        files = files[: args.limit]

    print("=== anonymize_resumes ===")
    print(f"input : {args.input} ({len(files)} files)")
    print(f"output: {args.output}")
    if not files:
        print("未找到简历。请把 docx/pdf/txt 放到 data/raw_real_resumes/")
        write_json(
            args.output / "anonymize_report.json",
            {"cases": 0, "message": "empty input", "input": str(args.input)},
        )
        return 0

    rows: list[dict[str, Any]] = []
    totals: Counter = Counter()
    for path in files:
        row = process_one(
            path,
            args.output,
            dry_run=args.dry_run,
            enable_ocr=args.ocr,
            ocr_engine=args.ocr_engine,
        )
        rows.append(row)
        totals.update(row.get("replacements") or {})
        flag = row["status"]
        print(f"[{flag}] {path.name} -> {row.get('output_txt')} repl={row.get('replacements')}")

    report = {
        "cases": len(rows),
        "dry_run": args.dry_run,
        "ocr_enabled": bool(args.ocr),
        "ocr_engine": args.ocr_engine if args.ocr else None,
        "input": str(args.input),
        "output": str(args.output),
        "replacement_totals": dict(totals),
        "needs_review": [r["source"] for r in rows if r["status"] == "needs_review"],
        "empty_or_unreadable": [r["source"] for r in rows if r["status"] == "empty_or_unreadable"],
        "rows": rows,
        "policy": {
            "name_strategy": "label_line + first_line_only (no blanket 2-4 hanzi replace)",
            "pdf_policy": "text-only export",
            "forbidden": ["llm_match_labeling", "auto_train_sbert", "commit_raw_resumes"],
        },
    }
    if not args.dry_run:
        write_json(args.output / "anonymize_report.json", report)
        write_json(
            args.output / "manifest.json",
            [
                {
                    "source": r["source"],
                    "stem": r["stem"],
                    "txt": r.get("output_txt"),
                    "docx": r.get("output_docx"),
                    "status": r["status"],
                }
                for r in rows
            ],
        )
    print("---")
    print(f"done cases={len(rows)} totals={dict(totals)}")
    print("请人工抽查至少 5 份 txt，确认无真名/手机/学校漏网后再进入分拣。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
