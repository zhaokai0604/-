"""生成/刷新 data/eval/match_cases.json（50+ 脱敏样例）。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "eval" / "match_cases.json"

BASE = [
    ("da-strong", "实习经历：使用 Python 与 SQL 完成用户行为数据清洗，搭建 Tableau 看板，周活跃提升 12%。技能：Python、SQL、Excel、可视化。", "数据分析师，要求 Python、SQL、数据可视化、指标分析", 5, "强匹配"),
    ("da-synonym", "项目：负责业务报表自动化，用 pandas 处理订单明细，并输出经营分析结论。", "数据分析师，要求 Python、SQL、数据可视化", 4, "同义表达（pandas≈Python）"),
    ("da-weak-metric", "参与了很多数据分析相关工作，比较熟悉业务。", "数据分析师，要求 Python、SQL、可视化", 2, "相关但证据弱"),
    ("fe-strong", "前端开发实习：使用 Vue3 + TypeScript 完成后台管理组件，对接 REST 接口，优化首屏加载。", "前端开发工程师，熟悉 Vue/React、JavaScript、TypeScript、组件化", 5, "前端强匹配"),
    ("fe-vs-be", "后端实习：Spring Boot 开发订单接口，MySQL 与 Redis 缓存优化。", "前端开发，要求 Vue、React、CSS", 1, "跨岗难负例"),
    ("pm-strong", "产品实习：负责需求调研与竞品分析，输出 PRD，用 Figma 绘制原型并跟进迭代。", "产品经理助理，要求需求分析、原型、PRD、用户研究", 5, "产品强匹配"),
    ("pm-partial", "运营实习：负责活动策划与用户增长，复盘转化率。", "产品经理，要求 PRD、原型、需求分析", 2, "部分相关"),
    ("media-strong", "新媒体运营：小红书内容策划与排版，单篇阅读 2.3 万，涨粉 800，完成数据复盘。", "新媒体运营，要求小红书、文案、数据分析、涨粉", 5, "新媒体强匹配"),
    ("media-vs-da", "新媒体运营：负责短视频剪辑与文案。", "数据分析师，要求 Python SQL 建模", 1, "跨岗"),
    ("be-strong", "后端项目：FastAPI 设计权限接口，MySQL 建模，Redis 缓存热点，完成部署。", "后端开发，要求 Python、接口、MySQL、Redis", 5, "后端强匹配"),
    ("be-keyword-miss-semantic-hit", "服务端开发：完成用户中心 API，数据库读写分离与缓存加速。", "后端工程师，要求接口开发、MySQL、Redis", 4, "关键词少但语义近"),
    ("generic-poor", "性格开朗，学习能力强，熟悉办公软件。", "Java 后端开发，要求 Spring、微服务", 1, "几乎不匹配"),
    ("excel-vs-vba", "用 VBA 处理过十万行销售明细并自动生成周报。", "数据分析专员，要求 Excel 数据处理与报表", 4, "细粒度难负/近义"),
    ("design-strong", "电商美工：Photoshop 制作主图与详情页，上新 30 套，点击率提升 8%。", "电商美工，要求 PS、详情页、视觉转化", 5, "设计岗"),
    ("design-vs-frontend", "平面设计：海报与品牌视觉物料制作。", "前端开发，要求 Vue JavaScript", 1, "跨岗"),
]

EXTRA = [
    ("da-powerbi", "实习：用 Power BI 做销售漏斗看板，梳理转化指标并周报复盘。", "数据分析，要求 PowerBI、指标、可视化", 4, "BI工具"),
    ("da-hive", "项目：Hive SQL 汇总日志，输出留存与活跃报表。", "数据分析师，要求 SQL、数据仓库、报表", 4, "仓数近义"),
    ("da-vs-pm", "简历：Python 建模与特征工程，AUC 提升 3%。", "产品经理，要求 PRD 原型需求", 1, "跨岗"),
    ("da-intern-mid", "数据分析实习：协助清洗问卷数据，用 Excel 透视表统计。", "数据分析专员，要求 Excel、统计、报表", 3, "中等匹配"),
    ("fe-react", "前端：React + Hooks 开发活动页，封装通用组件 12 个。", "前端工程师，要求 React、组件化、JavaScript", 5, "React强"),
    ("fe-css", "负责页面样式还原与响应式适配，熟悉 HTML/CSS。", "前端开发，要求 HTML CSS 响应式", 4, "偏样式"),
    ("fe-vs-design", "Vue 开发管理后台表格与表单。", "电商美工，要求 PS 详情页", 1, "跨岗"),
    ("be-java", "Java Spring Boot 订单服务，MyBatis 访问 MySQL。", "后端开发，要求 Java Spring MySQL", 5, "Java强"),
    ("be-docker", "参与服务容器化，编写 Dockerfile 并协助部署。", "后端/运维，要求部署、Docker、接口", 3, "偏运维"),
    ("be-vs-da", "Redis 缓存与接口限流优化。", "数据分析，要求 Python 可视化", 1, "跨岗"),
    ("pm-axure", "用 Axure 画原型，组织评审并跟进开发排期。", "产品助理，要求原型、需求、沟通", 4, "原型工具"),
    ("pm-vs-ops", "输出 PRD 与用户故事。", "新媒体运营，要求小红书文案", 1, "跨岗"),
    ("ops-douyin", "抖音账号运营，完播率 35%，投放 ROI 1.8。", "短视频运营，要求抖音、完播率、投放", 5, "短视频"),
    ("ops-wechat", "公众号选题与排版，月更 8 篇，打开率 12%。", "新媒体，要求公众号、文案、数据", 4, "公众号"),
    ("ops-vs-be", "负责社群活动与裂变增长。", "后端开发，要求 Java 接口", 1, "跨岗"),
    ("design-ai", "Illustrator 绘制图标与海报，服务店铺大促。", "视觉设计，要求 AI、海报、品牌", 4, "AI设计"),
    ("design-detail", "详情页转化优化，加购率提升 6%。", "电商美工，要求详情页、转化", 5, "转化设计"),
    ("video-pr", "Premiere 剪辑宣传片，交付 15 条成片。", "影视后期，要求 PR、剪辑、包装", 5, "剪辑"),
    ("video-vs-da", "AE 做片头包装。", "数据分析师，要求 SQL", 1, "跨岗"),
    ("teach-assist", "高等数学助教，整理题库并答疑 40+ 人次。", "教育辅导/助教，要求讲解、耐心、总结", 3, "教辅"),
    ("research-lab", "实验室助手：文献调研与实验记录整理。", "科研助理，要求文献、实验记录", 3, "科研"),
    ("sale-intern", "电话销售实习，日均有效沟通 20 通，成交 3 单。", "销售专员，要求沟通、成交、抗压", 4, "销售"),
    ("sale-vs-fe", "地推与客户维护。", "前端开发，要求 Vue", 1, "跨岗"),
    ("hr-assist", "招聘助理：筛选简历 200+，安排面试并写纪要。", "HR 助理，要求简历筛选、沟通、组织", 4, "人力"),
    ("finance-excel", "财务实习：费用报销核对，Excel 做月度台账。", "财务助理，要求细心、Excel、台账", 4, "财务"),
    ("finance-vs-be", "熟悉增值税发票入账流程。", "后端工程师，要求 Python", 1, "跨岗"),
    ("da-abtest", "参与 A/B 实验分析，输出显著性结论与建议。", "数据分析，要求实验、统计、指标", 4, "实验"),
    ("da-etl", "编写定时 ETL 脚本，保证日报准时产出。", "数据开发/分析，要求 ETL、SQL、自动化", 4, "ETL"),
    ("fe-ts", "TypeScript 重构旧项目，降低运行时错误。", "前端，要求 TypeScript、工程化", 4, "TS"),
    ("fe-webpack", "优化打包体积，首屏减少 28%。", "前端性能优化，要求工程化、性能", 4, "性能"),
    ("be-mq", "接入消息队列削峰，失败重试可观测。", "后端，要求消息队列、可靠性", 3, "MQ"),
    ("be-auth", "实现 JWT 登录与权限中间件。", "后端，要求认证授权、接口安全", 4, "鉴权"),
    ("pm-roadmap", "维护版本路线图，协调设计与研发里程碑。", "产品经理，要求规划、协作、迭代", 4, "规划"),
    ("pm-user-interview", "完成 10 场用户访谈并提炼痛点。", "产品/用研，要求用户研究、访谈", 4, "用研"),
    ("media-script", "撰写短视频脚本 20 条，平均点赞 1.2k。", "内容运营，要求脚本、文案、数据", 4, "脚本"),
    ("media-seo", "负责站点 SEO 关键词布局与周报。", "运营，要求 SEO、内容、分析", 3, "SEO"),
    ("campus-org", "学生会宣传部：策划迎新活动，覆盖 800 人。", "综合岗/管培，要求组织、宣传、执行", 3, "校园"),
    ("comp-award", "获省级数学建模二等奖，负责建模与论文。", "数据分析/建模相关岗位", 4, "竞赛"),
    ("eng-cet", "英语六级 520，可阅读技术文档。", "任何技术岗附加项", 2, "弱加分项单独"),
    ("mismatch-chef", "中餐烹饪技能与后厨实习。", "Java 后端开发", 1, "完全无关"),
    ("mismatch-sport", "校足球队主力，组织训练。", "前端工程师", 1, "完全无关"),
    ("da-sql-only", "只会写基础 SELECT，无项目量化。", "高级数据分析，要求建模与实验", 2, "偏弱"),
    ("fe-jquery", "维护 jQuery 老页面，修缺陷。", "前端，要求 Vue/React 现代框架", 2, "技术栈偏旧"),
    ("be-crud", "完成增删改查接口，无高并发场景。", "后端，要求高并发与缓存", 2, "深度不足"),
    ("hybrid-full", "全栈：Vue 前端 + FastAPI 后端，MySQL 存储，独立上线校园二手平台，日活 120。", "全栈/后端/前端均可，要求项目闭环", 5, "综合强"),
    ("hybrid-partial", "写过课程设计网站，功能较简单。", "全栈工程师，要求独立交付", 2, "偏弱综合"),
]


def main() -> None:
    cases = [
        {"id": cid, "resume": resume, "job": job, "label": label, "note": note}
        for cid, resume, job, label, note in BASE + EXTRA
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "version": 2,
                "description": "高校简历-岗位匹配弱标注评测集（脱敏合成）50+",
                "cases": cases,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(cases)} cases -> {OUT}")


if __name__ == "__main__":
    main()
