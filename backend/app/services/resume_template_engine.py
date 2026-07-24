"""简历模板推荐：按目标岗位与简历结构匹配参考模板。"""

from __future__ import annotations

from typing import Any

TEMPLATE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "tech_standard",
        "name": "技术岗标准版",
        "categories": ["前端开发", "后端开发", "数据分析", "测试", "运维"],
        "keywords": ["开发", "工程师", "python", "java", "sql", "数据"],
        "sections": ["个人信息", "求职意向", "教育背景", "项目经历", "实习经历", "专业技能", "证书荣誉"],
        "highlights": ["项目经历前置", "技术栈与岗位 JD 对齐", "每条经历含动作 + 结果 + 量化"],
        "tips": "优先写 2–3 个与目标岗位最相关的项目，避免堆砌无关课程作业。",
    },
    {
        "id": "product_general",
        "name": "产品 / 运营通用版",
        "categories": ["产品经理", "运营", "市场"],
        "keywords": ["产品", "运营", "用户", "增长", "需求", "策划"],
        "sections": ["个人信息", "求职意向", "教育背景", "实习 / 项目经历", "校园实践", "技能与工具", "自我评价"],
        "highlights": ["突出用户洞察与数据驱动", "写清需求-方案-结果闭环", "体现跨部门协作"],
        "tips": "用 STAR 描述项目，强调你解决了什么问题、带来了什么指标变化。",
    },
    {
        "id": "finance_accounting",
        "name": "财会金融版",
        "categories": ["财务", "会计", "金融", "审计"],
        "keywords": ["财务", "会计", "审计", "金融", "excel", "报表"],
        "sections": ["个人信息", "求职意向", "教育背景", "实习经历", "专业证书", "技能", "校内实践"],
        "highlights": ["证书与实习并列展示", "突出报表/核算/风控相关经历", "表达严谨无口语化"],
        "tips": "若有 CPA、初级会计等证书请单独列出；实习经历写具体模块与产出。",
    },
    {
        "id": "design_creative",
        "name": "设计创意版",
        "categories": ["设计", "UI", "视觉", "多媒体"],
        "keywords": ["设计", "ui", "ux", "视觉", "作品集", "figma"],
        "sections": ["个人信息", "求职意向", "作品集链接", "项目经历", "教育背景", "技能工具", "获奖经历"],
        "highlights": ["作品集链接醒目", "项目配结果说明", "工具链与风格标签清晰"],
        "tips": "简历正文精简，把视觉作品放到作品集；每条项目说明你的角色与交付物。",
    },
    {
        "id": "campus_fresh",
        "name": "应届生通用版",
        "categories": ["default", "通用", "实习"],
        "keywords": [],
        "sections": ["个人信息", "求职意向", "教育背景", "实习经历", "项目 / 竞赛", "技能", "自我评价"],
        "highlights": ["一页纸原则", "教育背景写核心课程与排名", "无实习时用项目/竞赛补位"],
        "tips": "经历不足时，把课程设计、竞赛、社团负责内容写具体，避免空泛形容词。",
    },
]


def recommend_resume_templates(
    target_position: str = "",
    weight_template: str = "default",
    sections: dict[str, list[str]] | None = None,
    missing_keywords: list[str] | None = None,
) -> dict[str, Any]:
    sections = sections or {}
    missing_keywords = missing_keywords or []
    target = (target_position or "").strip().lower()
    template_key = (weight_template or "default").strip()

    scored: list[dict[str, Any]] = []
    for item in TEMPLATE_CATALOG:
        score, reasons = _score_template(item, target, template_key, sections, missing_keywords)
        if score <= 0:
            continue
        scored.append(
            {
                "id": item["id"],
                "name": item["name"],
                "match_score": score,
                "reasons": reasons,
                "sections": item["sections"],
                "highlights": item["highlights"],
                "tips": item["tips"],
            }
        )

    scored.sort(key=lambda row: row["match_score"], reverse=True)
    if not scored:
        fallback = TEMPLATE_CATALOG[-1]
        scored = [
            {
                "id": fallback["id"],
                "name": fallback["name"],
                "match_score": 1,
                "reasons": ["未识别明确岗位类型，推荐应届生通用结构"],
                "sections": fallback["sections"],
                "highlights": fallback["highlights"],
                "tips": fallback["tips"],
            }
        ]

    top = scored[:3]
    return {
        "summary": f"根据岗位「{target_position or '通用'}」推荐 {len(top)} 套简历结构参考。",
        "target_position": target_position or "通用",
        "templates": top,
    }


def list_template_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "categories": item["categories"],
            "sections": item["sections"],
            "highlights": item["highlights"],
            "tips": item["tips"],
        }
        for item in TEMPLATE_CATALOG
    ]


def _score_template(
    item: dict[str, Any],
    target: str,
    template_key: str,
    sections: dict[str, list[str]],
    missing_keywords: list[str],
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    for category in item.get("categories") or []:
        cat = str(category).lower()
        if cat in target or cat in template_key.lower():
            score += 4
            reasons.append(f"匹配岗位类型：{category}")

    for keyword in item.get("keywords") or []:
        kw = str(keyword).lower()
        if kw and kw in target:
            score += 2
            reasons.append(f"岗位关键词命中：{keyword}")

    if item["id"] == "campus_fresh" and not target:
        score += 2
        reasons.append("适合尚未明确岗位方向的简历结构")

    section_keys = {str(key).lower() for key in sections.keys()}
    core = {"internship", "projects", "skills", "education", "campus"}
    if item["id"] == "tech_standard" and (core & section_keys):
        score += 2
        reasons.append("已识别项目/实习/技能模块，技术岗模板契合度高")

    missing_sections = []
    for key in ("internship", "projects", "skills"):
        if key not in section_keys or not sections.get(key):
            missing_sections.append(key)
    if missing_sections and item["id"] in {"tech_standard", "campus_fresh"}:
        score += 2
        reasons.append("模板可补齐当前缺失的核心模块结构")

    if missing_keywords and item["id"] in {"tech_standard", "product_general"}:
        score += 1
        reasons.append("模板强调技能/项目模块，便于补齐缺失关键词")

    if not reasons and item["id"] == "campus_fresh":
        score = 1
        reasons.append("通用应届生结构")

    return score, reasons[:3]
