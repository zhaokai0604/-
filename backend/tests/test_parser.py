from app.services.parser import (
    _junk_text_ratio,
    detect_sections,
    detect_target_from_filename,
    detect_target_position,
    evaluate_parse_quality,
    extract_contact_entities,
    extract_keywords,
    extract_name_hint,
    extract_skill_phrases,
)


def test_extract_skill_phrases_finds_tech_stack():
    text = "熟悉 Python、Vue3 与 MySQL，参与数据分析项目。"
    phrases = extract_skill_phrases(text)
    lowered = {item.lower() for item in phrases}
    assert "python" in lowered
    assert any("vue" in item.lower() for item in phrases)
    assert "mysql" in lowered


def test_extract_contact_entities_finds_email_and_phone():
    text = "邮箱：zhangsan@example.com 手机 13800138000"
    entities = extract_contact_entities(text)
    assert entities["email"] == "zhangsan@example.com"
    assert entities["phone"] == "13800138000"


def test_extract_contact_entities_finds_template_contact_fields():
    text = "现 居：西安\n电 话：133-1234-5678\n邮 箱：aaaa@qq.com\n微 信：aaaa12345\n期望薪资：3K-5K"
    entities = extract_contact_entities(text)
    assert entities["email"] == "aaaa@qq.com"
    assert entities["phone"] == "13312345678"
    assert entities["wechat"] == "aaaa12345"
    assert entities["expected_salary"] == "3K-5K"


def test_extract_keywords_prioritizes_skill_phrases():
    text = "Python Python Python 负责日常事务处理"
    keywords = extract_keywords(text, limit=5)
    assert keywords[0].lower().startswith("python")


def test_detect_sections_with_chinese_headings():
    text = """
成娇
手机：13800138000
邮箱：cj@example.com

求职意向：平面设计 / 影视后期剪辑

教育背景
2019.09-2023.06 某某大学 视觉传达设计 本科

实习经历
2022.07-2022.12 某传媒公司 平面设计助理
负责海报与短视频封面设计，完成 30+ 套视觉物料

项目经历
2023.03-2023.06 品牌宣传短片剪辑项目
使用 PR、AE 完成片头包装，播放量 5w+

专业技能
Photoshop、Premiere、After Effects、剪映
"""
    sections = detect_sections(text)
    assert sections["basic_info"]
    assert any("13800138000" in line for line in sections["basic_info"])
    assert sections["education"]
    assert sections["internship"]
    assert sections["projects"]
    assert sections["skills"]
    assert extract_name_hint(sections, text) == "成娇"


def test_detect_sections_splits_table_like_line():
    text = "个人信息 | 姓名 | 成娇 | 电话 | 13800138000 | 邮箱 | cj@example.com\n教育背景\n某某大学 本科"
    sections = detect_sections(text)
    assert any("成娇" in line for line in sections["basic_info"])
    assert sections["education"]


def test_detect_sections_ignores_heading_only_lines():
    text = "教育背景\n某某大学 视觉传达 2020-2024\n实习经历\n2023 某公司 设计助理"
    sections = detect_sections(text)
    assert not any(line.strip() == "教育背景" for line in sections["education"])
    assert any("某某大学" in line for line in sections["education"])
    assert sections["internship"]


def test_detect_sections_keeps_major_under_education_heading():
    text = "教育背景\n人力资源管理\n实习经历\n招聘助理：筛选简历、安排面试。\n技能\n沟通、组织、Office\n"
    sections = detect_sections(text)
    assert any("人力资源管理" in line for line in sections["education"])
    assert not any("人力资源管理" in line for line in sections["basic_info"])
    assert sections["internship"]
    assert sections["skills"]


def test_detect_sections_splits_pipe_and_tab_table_cells():
    text = "教育背景\t某某大学 本科 数据科学\n技能 | Python | SQL | Excel"
    sections = detect_sections(text)
    assert sections["education"]
    assert any("某某大学" in line for line in sections["education"])
    skills_blob = " ".join(sections.get("skills") or [])
    assert "Python" in skills_blob or "SQL" in skills_blob


def test_backfill_moves_education_out_of_basic_info_without_duplicating():
    text = "基本信息\n张三\n2020-2024 某某大学 计算机科学与技术 本科\n专业技能\nPython"
    sections = detect_sections(text)
    edu_hits = [line for line in sections.get("education") or [] if "某某大学" in line]
    basic_hits = [line for line in sections.get("basic_info") or [] if "某某大学" in line]
    assert edu_hits
    assert not basic_hits


def test_internship_duty_with_tools_stays_in_internship():
    text = """
实习经历
2023.07-2023.12 某科技公司 运营助理
负责使用 Excel 与 Python 整理活动数据，协助完成周报
专业技能
Python、Excel
"""
    sections = detect_sections(text)
    intern_blob = "\n".join(sections.get("internship") or [])
    assert "整理活动数据" in intern_blob
    assert "Python" in "\n".join(sections.get("skills") or [])


def test_junk_ratio_and_parse_quality_thresholds():
    assert _junk_text_ratio("a b c d e f\n!!!\n@@@") > 0.3
    rich = {
        "basic_info": ["张三", "手机：13800138000"],
        "education": ["某某大学 本科"],
        "internship": ["某公司实习，负责运营"],
        "projects": ["数据分析项目"],
        "skills": ["Python SQL"],
    }
    text = "张三\n手机：13800138000\n某某大学 本科\n某公司实习，负责运营\n数据分析项目\nPython SQL\n" * 3
    quality, warnings = evaluate_parse_quality(text, rich, [], ".docx")
    assert quality in {"high", "medium"}
    low_quality, _ = evaluate_parse_quality("短", {"basic_info": ["张三"]}, [], ".pdf")
    assert low_quality == "low"


def test_detect_target_from_filename():
    stem = "成娇-求职简历(平面设计、影视后期剪辑)"
    target = detect_target_from_filename(stem)
    assert "平面设计" in target
    assert "影视后期" in target or "剪辑" in target


def test_detect_target_position_merges_split_label_value():
    text = "刘欣\n求职意向：\n新媒体运营\n期望薪资：\n3K-5K"
    sections = detect_sections(text)
    assert detect_target_position(text, sections) == "新媒体运营"


def test_extract_name_from_label():
    text = "姓名：成娇\n电话：13800138000"
    sections = detect_sections(text)
    assert extract_name_hint(sections, text) == "成娇"


def test_detect_sections_splits_inline_headings_from_template_text():
    text = """
杨佳雪
猫柒互娱网络公司
实习 负责线上平面素材制作、图片处理等工作 协助完成运营相关视觉物料设计与优化 配合团队完成日常运营辅助任务，执行力强 陕西机电职业技术学院
专科 获得 Uskills 活动 “坚持之星” 称号 获得校园摄影大赛二等奖 持有 HarmonyOS 应用开发基础证书 专业技能 办公软件：熟练使用 Word / Excel / PPT，掌握办公自动化操作 设计剪辑：熟练使用 PS、PR、AE 等专业软件 自我评价 为人踏实负责、学习能力强，具备良好的沟通协调与团队协作能力。
"""
    sections = detect_sections(text)
    assert any("负责线上平面素材制作" in line for line in sections["internship"])
    assert any("陕西机电职业技术学院" in line for line in sections["education"])
    assert any("办公软件" in line for line in sections["skills"])
    assert any("坚持之星" in line or "HarmonyOS" in line for line in sections["awards"])
    assert any("为人踏实负责" in line for line in sections["summary"])


def test_detect_sections_recognizes_common_alias_headings():
    text = """
校内外经历
学生会宣传部干事，负责公众号推文排版与活动拍摄

职业技能
熟练使用 Excel、PPT、Canva、剪映

证书荣誉
大学英语四级 校级优秀学生干部
"""
    sections = detect_sections(text)
    assert any("学生会宣传部" in line for line in sections["campus"])
    assert any("Canva" in line for line in sections["skills"])
    assert any("优秀学生干部" in line for line in sections["awards"])


def test_detect_sections_moves_personal_honor_out_of_skills():
    text = """
专业技能
Photoshop、Premiere、After Effects、剪映
个人荣誉：英语初级 计算机初级
"""
    sections = detect_sections(text)
    assert any("Photoshop" in line for line in sections["skills"])
    assert any("英语初级" in line for line in sections["awards"])


def test_detect_sections_keeps_campus_named_projects_in_projects():
    text = """
项目经历
校园二手交易数据分析：完成用户行为指标统计与可视化。
校园二手平台：Vue + FastAPI + MySQL，独立上线。
毕业设计：校园跑腿小程序需求分析与原型。
"""
    sections = detect_sections(text)
    assert len(sections["projects"]) >= 3
    assert not sections["campus"]


def test_detect_sections_keeps_product_intern_under_internship():
    text = """
实习经历
产品实习：输出 PRD，用 Figma 画原型并跟进迭代。
技能
沟通、组织、Office
"""
    sections = detect_sections(text)
    assert any("产品实习" in line for line in sections["internship"])
    assert not any("产品实习" in line for line in sections["skills"])
    assert not any("沟通" in line for line in sections["summary"])


def test_detect_sections_english_internship_heading():
    text = """
Education
B.S. Computer Science
Internship
Backend intern: FastAPI and MySQL.
Skills
Python, SQL, Docker
"""
    sections = detect_sections(text)
    assert any("Backend intern" in line for line in sections["internship"])
    assert any("Python" in line for line in sections["skills"])


def test_detect_sections_job_hope_not_internship_heading():
    text = "本人性格开朗，学习能力强。\n熟悉 Word、Excel，会一点 PS。\n希望从事运营相关工作。\n"
    sections = detect_sections(text)
    assert sections["skills"]
    assert not sections["internship"]


def test_detect_sections_keeps_major_with_xitong_under_education():
    text = "赵六 / 数据分析\n教育背景\n信息管理与信息系统\n项目经历\nSales dashboard with Power BI\n"
    sections = detect_sections(text)
    assert any("信息管理与信息系统" in line for line in sections["education"])
    assert not any("信息管理与信息系统" in line for line in sections["projects"])


def test_detect_sections_does_not_promote_media_duties_to_projects():
    text = "实习经历\n学生会宣传部干事，负责公众号推文排版与活动拍摄\n证书：普通话二级、英语四级\n"
    sections = detect_sections(text)
    assert not sections["projects"]
    assert sections["campus"]
    assert not sections["awards"]


def test_detect_sections_dedupes_repeated_extracted_lines():
    text = "项目经历\n数据分析项目：清洗数据并输出报告\n数据分析项目：清洗数据并输出报告\n"
    sections = detect_sections(text)
    assert sections["projects"] == ["数据分析项目：清洗数据并输出报告"]


def test_detect_sections_keeps_summary_and_course_text_out_of_projects():
    text = """
    教育背景
    某某大学 计算机专业 本科
    主修课程：Python程序设计、数据库系统、Web前端设计
    自我评价
    性格踏实，期待在专业平台获得成长，具备良好的沟通能力。
    """
    sections = detect_sections(text)
    assert not sections["projects"]
    assert any("期待" in line for line in sections["summary"])


def test_detect_sections_keeps_labeled_skill_prose_out_of_internship():
    text = """
    技能证书
    视频剪辑：熟练使用 PR、AE，擅长字幕动画与成片输出。
    平面设计：精通 PS，可制作海报与封面。
    自我评价
    学习能力强，责任心强。
    """
    sections = detect_sections(text)
    assert not sections["internship"]
    assert sections["skills"]


def test_detect_sections_does_not_create_awards_or_projects_for_empty_or_embedded_honors():
    text = """
    教育背景
    某某大学 本科
    学业成绩：专业前10%，多次获得学校奖学金
    项目/课堂实践经历
    课程项目：校园公众号模拟运营
    荣誉：无
    """
    sections = detect_sections(text)
    assert not sections["awards"]
    assert sections["projects"]
    assert not sections["internship"]


def test_detect_sections_recovers_summary_before_trailing_heading():
    """乱序双栏：自我评价正文出现在标题之前。"""
    text = """
    教育背景
    某某大学 软件技术 专科
    本人学习能力强，具备良好的沟通协调与团队协作能力，责任心强，做事踏实细致。
    自我评价
    """
    sections = detect_sections(text)
    assert sections["summary"]
    assert any("学习能力强" in line for line in sections["summary"])


def test_detect_sections_keeps_summary_with_incidental_skill_words():
    text = """
    自我评价
    具备扎实的护理专业知识与临床实操能力，熟练掌握内科护理核心技能。工作严谨细致、共情力强，善于沟通协调。
    """
    sections = detect_sections(text)
    assert sections["summary"]
    assert any("共情" in line or "沟通" in line for line in sections["summary"])


def test_detect_sections_rejects_social_practice_honor_as_internship():
    text = """
    教育背景
    某某大学 数字媒体技术
    3、2025年暑期“三下乡”社会实践活动省级优秀团队
    4、2025年五四表彰优秀团员
    自我评价
    本人沟通表达能力出色，抗压能力强。
    """
    sections = detect_sections(text)
    assert not sections["internship"]
    assert sections["summary"]


def test_detect_sections_does_not_treat_job_intent_intern_as_internship():
    text = """
    求职意向：新媒体运营实习生
    教育背景
    某某大学 软件技术
    项目/课堂实践经历
    课程项目：校园公众号模拟运营
    自我评价
    学习力强，踏实细心。
    """
    sections = detect_sections(text)
    assert not sections["internship"]
    assert sections["projects"]


def test_detect_sections_campus_roles_under_work_experience_not_internship():
    text = """
    工作经验
    1、2025年12月担任景区讲解员。
    2、2024至今，某高校24班团支书。
    自我评价
    本人综合素养良好，沟通能力出色。
    """
    sections = detect_sections(text)
    assert not sections["internship"]
    assert sections["campus"] or sections["summary"]


def test_detect_sections_keeps_embedded_education_scholarship_in_education():
    text = """
    教育背景
    某某大学 人工智能专业 硕士
    学业表现：GPA 3.7/5.0，排名前5%，连续三年获得校级一等奖学金
    技能
    Python、SQL、PyTorch
    """
    sections = detect_sections(text)
    assert sections["education"]
    assert not sections["awards"]


def test_detect_sections_keeps_competition_participation_in_campus():
    text = """
    教育背景
    某某大学 护理学 本科
    校园经历
    参与组织护理技能大赛、校园文化节等活动4场
    """
    sections = detect_sections(text)
    assert sections["campus"]
    assert not sections["awards"]


def test_detect_sections_does_not_promote_social_practice_project_to_projects():
    text = """
    教育背景
    某某大学 酒店管理专业
    校园经历
    2025年暑期三下乡社会实践项目获得省级优秀项目
    志愿服务：参加校园迎新活动
    """
    sections = detect_sections(text)
    assert sections["campus"]
    assert not sections["projects"]
