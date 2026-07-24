from app.services.parser import (
    detect_sections,
    detect_target_from_filename,
    detect_target_position,
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
