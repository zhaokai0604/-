"""生成解析评测集 data/eval/parse_cases.json（合成脱敏样本，无真实学生简历）。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "eval" / "parse_cases.json"

CASES = [
    {
        "id": "std-da",
        "gold_sections": ["basic_info", "education", "internship", "projects", "skills"],
        "text": """张三
求职意向：数据分析实习生
教育背景
2022-2025 某某职业技术学院 大数据技术
实习经历
2024.06-2024.09 某零售公司 数据分析实习：使用 Python 与 SQL 清洗订单数据，搭建看板。
项目经历
校园二手交易数据分析：完成用户行为指标统计与可视化。
技能证书
Python、SQL、Excel、Tableau
""",
    },
    {
        "id": "std-fe",
        "gold_sections": ["basic_info", "education", "internship", "skills"],
        "text": """李四
手机：13800000000
教育背景
某某大学 软件工程 本科
实习经历
前端开发实习：Vue3 + TypeScript 完成后台管理页面。
专业技能
JavaScript、Vue、HTML、CSS
""",
    },
    {
        "id": "std-be",
        "gold_sections": ["education", "projects", "skills"],
        "text": """教育背景
计算机科学与技术 本科
项目经历
订单服务：Spring Boot + MySQL + Redis 完成接口与缓存。
技能
Java、Spring Boot、MySQL、Redis
""",
    },
    {
        "id": "std-pm",
        "gold_sections": ["basic_info", "education", "internship", "campus"],
        "text": """王五
求职意向：产品经理助理
教育背景
电子商务 专科
实习经历
产品实习：输出 PRD，用 Figma 画原型并跟进迭代。
校园经历
学生会宣传部部长，组织迎新活动覆盖 500 人。
""",
    },
    {
        "id": "std-media",
        "gold_sections": ["education", "internship", "skills", "awards"],
        "text": """教育背景
网络与新媒体
实习经历
新媒体运营：小红书内容策划，单篇阅读 2 万。
技能证书
剪辑、文案、数据分析
获奖情况
校级新媒体运营大赛二等奖
""",
    },
    {
        "id": "edu-skills-only",
        "gold_sections": ["education", "skills"],
        "text": """教育背景
酒店管理与数字化运营
技能
Office、PS 基础、短视频剪辑
""",
    },
    {
        "id": "with-awards",
        "gold_sections": ["education", "projects", "awards", "skills"],
        "text": """教育背景
应用数学
项目经历
数学建模：负责建模与论文撰写。
获奖情况
省级数学建模二等奖
技能
Python、MATLAB
""",
    },
    {
        "id": "campus-heavy",
        "gold_sections": ["education", "campus", "skills"],
        "text": """教育背景
市场营销
校园经历
社团主席，策划 3 场校级活动。
技能
活动策划、沟通协调、PPT
""",
    },
    {
        "id": "en-heading",
        "gold_sections": ["education", "internship", "skills"],
        "text": """Education
B.S. Computer Science
Internship
Backend intern: FastAPI and MySQL.
Skills
Python, SQL, Docker
""",
    },
    {
        "id": "mixed-cn-en",
        "gold_sections": ["basic_info", "education", "projects", "skills"],
        "text": """赵六 / 数据分析
教育背景
信息管理与信息系统
项目经历
Sales dashboard with Power BI
Skills
SQL、Excel、Power BI
""",
    },
    {
        "id": "dense-headings",
        "gold_sections": ["education", "internship", "projects", "skills", "awards"],
        "text": """教育背景
智能科学与技术
实习经历
算法实习：参与样本标注与基线训练。
项目经历
垃圾分类小程序：负责后端接口。
技能证书
CET-6、Python
获奖情况
校级创新创业大赛铜奖
""",
    },
    {
        "id": "weak-structure",
        "gold_sections": ["basic_info", "skills"],
        "text": """本人性格开朗，学习能力强。
熟悉 Word、Excel，会一点 PS。
希望从事运营相关工作。
""",
    },
    {
        "id": "internship-project",
        "gold_sections": ["education", "internship", "projects"],
        "text": """教育背景
电子商务
实习经历
电商运营实习：负责店铺上新与数据复盘。
项目经历
毕业设计：校园跑腿小程序需求分析与原型。
""",
    },
    {
        "id": "design-resume",
        "gold_sections": ["education", "internship", "skills", "awards"],
        "text": """教育背景
视觉传达设计
实习经历
电商美工：Photoshop 制作主图与详情页。
技能
Photoshop、Illustrator、详情页设计
获奖情况
校级设计展入选
""",
    },
    {
        "id": "research-lite",
        "gold_sections": ["education", "campus", "skills"],
        "text": """教育背景
应用化学
校园经历
实验室助手：文献调研与实验记录整理。
技能
文献检索、实验记录、Origin
""",
    },
    {
        "id": "sale-hr",
        "gold_sections": ["education", "internship", "skills"],
        "text": """教育背景
人力资源管理
实习经历
招聘助理：筛选简历、安排面试。
技能
沟通、组织、Office
""",
    },
    {
        "id": "finance",
        "gold_sections": ["education", "internship", "skills"],
        "text": """教育背景
会计学
实习经历
财务实习：费用报销核对与月度台账。
技能
Excel、细心、台账
""",
    },
    {
        "id": "full-stack",
        "gold_sections": ["basic_info", "education", "projects", "skills"],
        "text": """钱七
求职意向：全栈开发
教育背景
软件技术
项目经历
校园二手平台：Vue + FastAPI + MySQL，独立上线。
技能
Vue、Python、MySQL、Linux
""",
    },
    {
        "id": "heading-noise",
        "gold_sections": ["summary", "education", "skills"],
        "text": """自我评价
乐观积极。
教育背景
物流管理
专业技能
仓储管理、Excel、沟通
""",
    },
    {
        "id": "multi-internship",
        "gold_sections": ["education", "internship", "skills"],
        "text": """教育背景
计算机应用
实习经历
2023 暑期：测试实习，编写用例 80+。
2024 暑期：后端实习，完成权限模块。
技能
Java、接口测试、MySQL
""",
    },
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "cases": CASES}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(CASES)} cases -> {OUT}")


if __name__ == "__main__":
    main()
