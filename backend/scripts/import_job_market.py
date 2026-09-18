"""Import publicly accessible job pages into a UTF-8, redacted job corpus.

This tool intentionally accepts an explicit URL manifest. It does not crawl
search engines, bypass login/CAPTCHA, or enumerate protected job-board APIs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib import parse, request, robotparser

DEGREE_PATTERNS = (
    ("doctorate", re.compile(r"博士|博士研究生|ph\.?d", re.I)),
    ("master", re.compile(r"硕士|研究生|master|postgraduate", re.I)),
    ("bachelor", re.compile(r"本科|学士|大学本科|bachelor|undergraduate", re.I)),
    ("college", re.compile(r"大专|专科|高职|college diploma|associate degree", re.I)),
)
SKILL_TERMS = (
    "Python", "Java", "Go", "SQL", "Excel", "Power BI", "Tableau", "Figma", "PS", "PR", "AE",
    "Vue", "React", "JavaScript", "TypeScript", "FastAPI", "Django", "Spring Boot", "MySQL",
    "Redis", "Docker", "Linux", "Postman", "Selenium", "数据分析", "数据清洗", "数据可视化",
    "机器学习", "深度学习", "用户增长", "内容运营", "新媒体运营", "项目管理", "需求分析",
    "竞品分析", "原型设计", "文案策划", "短视频运营", "电商运营", "供应链管理",
)
CONTACT_RE = re.compile(r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|1[3-9]\d[\s-]?\d{4}[\s-]?\d{4})")


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg", "template"}:
            self._hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg", "template"} and self._hidden:
            self._hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)


def fetch_page(url: str, timeout: int = 20) -> tuple[str, str]:
    parsed = parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("只允许 http/https 公开页面 URL")
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    robots = robotparser.RobotFileParser(robots_url)
    try:
        robots.read()
        if not robots.can_fetch("简析智评-public-corpus/1.0", url):
            raise PermissionError("robots.txt 不允许采集该页面")
    except PermissionError:
        raise
    except Exception:
        # robots.txt 不可访问时不绕过安全策略，交由人工确认 URL 后再导入。
        raise RuntimeError("无法核验 robots.txt，请先人工确认该页面允许公开采集")
    req = request.Request(
        url,
        headers={"User-Agent": "JianxiResumePublicCorpus/1.0 (+local research; contact unavailable)"},
    )
    with request.urlopen(req, timeout=timeout) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace"), response.geturl()


def normalize_text(html: str) -> str:
    parser = VisibleTextParser()
    parser.feed(html)
    text = "\n".join(parser.parts)
    text = CONTACT_RE.sub("[已脱敏联系方式]", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:30000].strip()


def infer_degree(text: str) -> dict[str, str]:
    matches = [key for key, pattern in DEGREE_PATTERNS if pattern.search(text)]
    if not matches:
        return {"minimum": "unspecified", "preferred": "unspecified", "evidence": ""}
    rank = {"college": 1, "bachelor": 2, "master": 3, "doctorate": 4}
    minimum = matches[-1]
    if re.search(r"大专及以上|专科及以上", text, re.I):
        minimum = "college"
    elif re.search(r"本科及以上|本科优先", text, re.I):
        minimum = "bachelor"
    elif re.search(r"硕士及以上|硕士优先", text, re.I):
        minimum = "master"
    preferred = max(matches, key=lambda item: rank[item])
    evidence = "；".join(dict.fromkeys(pattern.pattern for key, pattern in DEGREE_PATTERNS if key in matches))
    return {"minimum": minimum, "preferred": preferred, "evidence": evidence}


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    return [term for term in SKILL_TERMS if term.lower() in lowered]


def build_record(url: str, html: str, final_url: str) -> dict[str, object]:
    text = normalize_text(html)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
    degree = infer_degree(text)
    skills = extract_skills(text)
    return {
        "id": "",
        "source_url": final_url,
        "source_url_requested": url,
        "source_type": "public_job_page",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "title": title[:200],
        "text_redacted": text,
        "education": degree,
        "skill_mentions": skills,
        "category": "",
        "target_position": "",
        "labels": {"must_skills": [], "nice_skills": [], "responsibilities": []},
        "review_status": "pending_manual_review",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导入公开岗位页面，输出 UTF-8 脱敏岗位样本")
    parser.add_argument("--urls", required=True, type=Path, help="每行一个公开 URL 的清单")
    parser.add_argument("--output", required=True, type=Path, help="输出 JSONL 路径")
    parser.add_argument("--delay", type=float, default=2.0, help="请求间隔秒数")
    args = parser.parse_args()
    urls = [line.strip() for line in args.urls.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    records: list[dict[str, object]] = []
    for index, url in enumerate(urls, 1):
        try:
            html, final_url = fetch_page(url)
            record = build_record(url, html, final_url)
            record["id"] = f"public-{index:05d}"
            records.append(record)
            print(f"[{index}/{len(urls)}] ok {url}")
        except Exception as exc:
            print(f"[{index}/{len(urls)}] skip {url}: {exc}", file=sys.stderr)
        if index < len(urls):
            time.sleep(max(0.0, args.delay))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"wrote {args.output} records={len(records)} encoding=utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
