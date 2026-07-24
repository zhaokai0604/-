from __future__ import annotations

from typing import Any


JOB_PROFILE_PRESETS: list[dict[str, str]] = [
    {
        "id": "frontend_engineer",
        "name": "前端开发校招模板",
        "category": "技术研发",
        "target_position": "前端开发工程师",
        "requirement_summary": "熟悉 HTML、CSS、JavaScript、TypeScript，掌握 Vue 或 React，了解组件化、工程化、接口联调与性能优化。",
        "description": "重点关注项目经历、技术栈匹配、组件封装、接口联调、页面性能、响应式适配和作品链接。",
    },
    {
        "id": "backend_engineer",
        "name": "后端开发校招模板",
        "category": "技术研发",
        "target_position": "后端开发工程师",
        "requirement_summary": "熟悉 Java/Python/Go 任一后端语言，掌握数据库、缓存、接口设计、权限认证、日志排查和基础部署。",
        "description": "重点关注服务端项目、接口职责、数据库设计、性能/稳定性指标、部署经验和问题排查能力。",
    },
    {
        "id": "java_engineer",
        "name": "Java 开发校招模板",
        "category": "技术研发",
        "target_position": "Java 开发工程师",
        "requirement_summary": "熟悉 Java、Spring Boot、MySQL、Redis，理解 RESTful 接口、事务、缓存、基础并发与常见设计模式。",
        "description": "适合 Java 后端、企业应用开发岗位；简历应突出 Spring 项目、数据库表设计、接口性能和工程规范。",
    },
    {
        "id": "python_engineer",
        "name": "Python 开发校招模板",
        "category": "技术研发",
        "target_position": "Python 开发工程师",
        "requirement_summary": "熟悉 Python 语法与常用库，了解 FastAPI/Django/Flask、数据库、爬虫/脚本自动化或数据处理经验。",
        "description": "突出 Python 项目实践、接口开发、自动化脚本、数据处理流程和可量化效率提升。",
    },
    {
        "id": "qa_engineer",
        "name": "测试工程师校招模板",
        "category": "技术研发",
        "target_position": "测试工程师",
        "requirement_summary": "了解软件测试流程、测试用例设计、缺陷管理，熟悉接口测试、自动化测试、Postman、JMeter 或 Selenium。",
        "description": "重点展示测试计划、用例覆盖、缺陷定位、自动化脚本和质量改进结果。",
    },
    {
        "id": "devops_engineer",
        "name": "运维/DevOps 校招模板",
        "category": "技术研发",
        "target_position": "运维工程师",
        "requirement_summary": "熟悉 Linux、Shell、Docker、Nginx、CI/CD、监控告警和基础网络知识，具备部署与故障排查意识。",
        "description": "突出部署流程、脚本自动化、监控告警、故障处理、服务器或云平台实践。",
    },
    {
        "id": "data_analyst",
        "name": "数据分析校招模板",
        "category": "数据",
        "target_position": "数据分析师",
        "requirement_summary": "熟悉 SQL、Excel、Python，了解统计分析、指标体系、数据清洗、可视化报表和业务分析方法。",
        "description": "简历应突出数据规模、分析结论、业务指标、可视化工具和分析结果带来的改进。",
    },
    {
        "id": "bi_engineer",
        "name": "数据开发/BI 模板",
        "category": "数据",
        "target_position": "数据开发/BI 工程师",
        "requirement_summary": "熟悉 SQL、数据仓库、ETL、报表开发、指标口径、数据建模，了解 Tableau/Power BI/FineBI 等工具。",
        "description": "重点关注数据链路、报表建设、指标统一、数据质量、自动化产出和业务看板。",
    },
    {
        "id": "algorithm_engineer",
        "name": "算法工程师校招模板",
        "category": "数据",
        "target_position": "算法工程师",
        "requirement_summary": "掌握机器学习、深度学习、Python、PyTorch/TensorFlow，熟悉特征工程、模型训练、评估指标和论文/竞赛实践。",
        "description": "突出算法项目、数据集规模、模型指标、调参过程、竞赛排名、论文或工程落地能力。",
    },
    {
        "id": "product_manager",
        "name": "产品经理校招模板",
        "category": "产品",
        "target_position": "产品经理",
        "requirement_summary": "具备用户研究、需求分析、竞品分析、原型设计、PRD 撰写、数据分析和跨团队沟通能力。",
        "description": "重点展示需求来源、用户痛点、方案取舍、原型/PRD、上线结果和指标变化。",
    },
    {
        "id": "product_operations",
        "name": "产品运营模板",
        "category": "运营",
        "target_position": "产品运营",
        "requirement_summary": "了解用户生命周期、活动策划、数据分析、内容配置、用户反馈收集、转化提升和产品迭代协作。",
        "description": "突出运营目标、用户分层、活动机制、转化/留存/活跃指标和跨部门协作。",
    },
    {
        "id": "new_media_operations",
        "name": "新媒体运营模板",
        "category": "运营",
        "target_position": "新媒体运营",
        "requirement_summary": "熟悉公众号、小红书、抖音等平台内容运营，具备选题策划、文案撰写、数据复盘和热点跟进能力。",
        "description": "重点展示账号增长、阅读/播放/互动数据、爆款内容、选题方法和内容矩阵经验。",
    },
    {
        "id": "content_operations",
        "name": "内容运营模板",
        "category": "运营",
        "target_position": "内容运营",
        "requirement_summary": "具备内容策划、编辑排版、专题运营、用户洞察、数据复盘和内容质量管理能力。",
        "description": "突出内容产量、阅读转化、专题效果、用户反馈、协作流程和内容规范建设。",
    },
    {
        "id": "user_operations",
        "name": "用户运营模板",
        "category": "运营",
        "target_position": "用户运营",
        "requirement_summary": "熟悉用户分层、社群运营、活动运营、用户增长、留存促活、数据分析和用户反馈处理。",
        "description": "重点展示社群规模、活跃率、转化率、留存提升、活动机制和用户洞察。",
    },
    {
        "id": "ecommerce_operations",
        "name": "电商运营模板",
        "category": "运营",
        "target_position": "电商运营",
        "requirement_summary": "了解商品上架、店铺活动、平台规则、流量分析、转化优化、库存协同和竞品分析。",
        "description": "突出 GMV、转化率、客单价、活动 ROI、商品优化和平台运营经验。",
    },
    {
        "id": "marketing_specialist",
        "name": "市场营销模板",
        "category": "市场",
        "target_position": "市场营销专员",
        "requirement_summary": "具备市场调研、品牌传播、活动策划、渠道推广、文案撰写和数据复盘能力。",
        "description": "重点展示活动规模、线索转化、曝光量、预算执行、渠道效果和项目协作。",
    },
    {
        "id": "ui_designer",
        "name": "UI/视觉设计模板",
        "category": "设计",
        "target_position": "UI/视觉设计师",
        "requirement_summary": "熟悉 Figma、Sketch、Photoshop、Illustrator，具备界面设计、视觉规范、交互理解和作品集呈现能力。",
        "description": "简历应突出作品集链接、设计项目、视觉规范、交互改进、工具链和设计结果。",
    },
    {
        "id": "accounting",
        "name": "财务会计模板",
        "category": "财务金融",
        "target_position": "财务/会计",
        "requirement_summary": "掌握会计基础、财务报表、Excel、费用审核、凭证整理、税务基础，优先具备初级会计等证书。",
        "description": "突出财务实习、报表处理、凭证/票据、核算流程、证书和严谨细致的工作习惯。",
    },
    {
        "id": "audit_assistant",
        "name": "审计助理模板",
        "category": "财务金融",
        "target_position": "审计助理",
        "requirement_summary": "了解审计流程、底稿整理、函证、抽凭、Excel 数据处理和财务报表基础。",
        "description": "重点展示审计项目协助、底稿质量、数据核对、风险意识和财会证书。",
    },
    {
        "id": "risk_control",
        "name": "金融风控模板",
        "category": "财务金融",
        "target_position": "风控专员",
        "requirement_summary": "了解金融产品、风险识别、数据分析、Excel/SQL、贷前贷后流程和合规意识。",
        "description": "突出数据分析、风险指标、案例审核、模型/规则理解和金融相关实习或课程。",
    },
    {
        "id": "hr_specialist",
        "name": "人力资源模板",
        "category": "职能",
        "target_position": "人力资源专员",
        "requirement_summary": "了解招聘、培训、员工关系、绩效、薪酬基础，具备沟通协调、信息整理和数据统计能力。",
        "description": "重点展示招聘流程、候选人沟通、活动组织、数据台账和跨部门协作。",
    },
    {
        "id": "admin_secretary",
        "name": "行政文秘模板",
        "category": "职能",
        "target_position": "行政/文秘",
        "requirement_summary": "具备办公软件、会议组织、文档管理、物资采购、流程执行、沟通协调和服务意识。",
        "description": "突出行政事务、会议/活动支持、流程优化、文档归档和细致执行能力。",
    },
    {
        "id": "legal_assistant",
        "name": "法务助理模板",
        "category": "职能",
        "target_position": "法务助理",
        "requirement_summary": "具备合同审核、法律检索、文书整理、合规意识、办公软件和基础民商法知识。",
        "description": "重点展示合同/文书处理、法律检索、案例分析、证书考试和严谨表达。",
    },
    {
        "id": "supply_chain",
        "name": "供应链/采购模板",
        "category": "供应链",
        "target_position": "供应链/采购专员",
        "requirement_summary": "了解采购流程、供应商管理、库存协同、成本意识、Excel 数据处理和跨部门沟通。",
        "description": "突出采购/物流实习、供应商沟通、库存数据、流程跟进、成本或效率改善。",
    },
    {
        "id": "foreign_trade",
        "name": "外贸业务模板",
        "category": "销售贸易",
        "target_position": "外贸业务员",
        "requirement_summary": "具备英语沟通、客户开发、询盘跟进、订单协调、跨境平台基础和国际贸易流程理解。",
        "description": "重点展示英语能力、客户沟通、订单跟进、展会/平台经验和销售转化数据。",
    },
    {
        "id": "customer_success",
        "name": "客户成功模板",
        "category": "销售服务",
        "target_position": "客户成功专员",
        "requirement_summary": "具备客户沟通、需求理解、问题跟进、产品培训、续费转化、数据复盘和服务意识。",
        "description": "突出客户维护、问题闭环、满意度、续费/转化、培训支持和跨团队协同。",
    },
]


def list_job_profile_presets() -> list[dict[str, str]]:
    return [dict(item) for item in JOB_PROFILE_PRESETS]


def get_job_profile_preset(preset_id: str) -> dict[str, str] | None:
    for item in JOB_PROFILE_PRESETS:
        if item["id"] == preset_id:
            return dict(item)
    return None


def preset_payload(preset: dict[str, Any]) -> dict[str, str]:
    return {
        "name": str(preset.get("name") or "").strip(),
        "category": str(preset.get("category") or "").strip(),
        "target_position": str(preset.get("target_position") or "").strip(),
        "requirement_summary": str(preset.get("requirement_summary") or "").strip(),
        "description": str(preset.get("description") or "").strip(),
        "status": "active",
    }
