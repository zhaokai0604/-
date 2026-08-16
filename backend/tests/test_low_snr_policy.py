from app.services.resume_rewriter import build_rewrite_preview
from app.services.score_engine import build_evidence, classify_resume_line, score_resume


def test_classify_skips_education_award_skills_for_metrics():
    assert classify_resume_line("特长：播音主持、视频剪辑、唱歌、美术设计") == "skills"
    assert classify_resume_line("2024年至今就读于陕西机电职业技术学院酒店管理与数字化运营专业") == "education"
    assert classify_resume_line("荣获陕西机电职业技术学院校园十佳歌手") == "award"
    assert classify_resume_line("2024年至今任校团委宣传部干事") == "role_title"
    assert classify_resume_line("负责公众号推文排版与活动拍摄") == "duty"


def test_low_snr_does_not_flag_education_skills_awards():
    sections = {
        "basic_info": ["张三"],
        "education": ["2024年至今就读于陕西机电职业技术学院酒店管理与数字化运营专业"],
        "campus": [
            "2024年至今任陕西机电职业技术学院校团委宣传部干事",
            "被评为2025年暑期三下乡社会实践活动校级先进个人",
            "荣获2026年陕西机电职业技术学院校园歌手大赛十佳歌手",
        ],
        "skills": ["特长：播音主持、视频剪辑、唱歌、美术设计"],
        "summary": ["本人综合素质良好，表达能力较强，能熟练使用WPS、Excel等办公软件。"],
    }
    text = "\n".join(
        [
            "特长：播音主持、视频剪辑、唱歌、美术设计",
            sections["education"][0],
            *sections["campus"],
            sections["summary"][0],
        ]
    )
    evidence = build_evidence(sections, text)
    zone_texts = " ".join(zone["text"] for zone in evidence["low_snr_zones"])
    assert "特长" not in zone_texts
    assert "就读于" not in zone_texts
    assert "十佳歌手" not in zone_texts
    assert "先进个人" not in zone_texts
    # 头衔或空泛可以提示，但不要求硬量化
    reasons = [zone["reason"] for zone in evidence["low_snr_zones"]]
    assert reasons
    assert not any("缺少量化结果或可验证产出" == reason for reason in reasons)
    assert any("不必硬凑百分比" in reason or "空泛" in reason for reason in reasons)


def test_rewrite_preview_avoids_metric_pressure_on_non_duty_lines():
    sections = {
        "education": ["2024年至今就读于某某学院酒店管理专业"],
        "campus": ["2024年至今任校团委宣传部干事"],
        "skills": ["特长：播音主持、视频剪辑"],
        "summary": ["综合素质良好，表达能力较强"],
        "internship": ["协助完成活动物料整理与现场执行"],
    }
    evidence = build_evidence(sections, "\n".join(sum(sections.values(), [])))
    preview = build_rewrite_preview(
        sections,
        {"missing_keywords": ["沟通"], "matched_keywords": [], "target_position": "新媒体运营"},
        evidence,
        "新媒体运营",
    )
    joined = " ".join(item["original"] for item in preview["items"])
    assert "就读于" not in joined
    assert "特长" not in joined
    focuses = " ".join(item["focus"] for item in preview["items"])
    assert "硬凑" in focuses or "有数据再写" in focuses or "空泛" in focuses


def test_score_penalty_message_mentions_no_forced_metrics():
    parsed = {
        "raw_text": (
            "特长：播音主持、视频剪辑\n"
            "2024年至今就读于某某学院酒店管理专业\n"
            "2024年至今任校团委宣传部干事\n"
            "负责校园活动宣传与推文排版\n"
            "综合素质良好，表达能力较强"
        ),
        "sections": {
            "skills": ["特长：播音主持、视频剪辑"],
            "education": ["2024年至今就读于某某学院酒店管理专业"],
            "campus": [
                "2024年至今任校团委宣传部干事",
                "负责校园活动宣传与推文排版",
            ],
            "summary": ["综合素质良好，表达能力较强"],
        },
        "detected_keywords": ["宣传", "推文"],
        "parse_quality": "high",
    }
    result = score_resume(parsed, "新媒体运营", "推文 活动 宣传")
    for zone in result.get("low_snr_zones") or []:
        assert classify_resume_line(zone["text"]) not in {"education", "skills", "award"}
    reasons = " ".join((result.get("low_snr_penalty") or {}).get("reasons") or [])
    if reasons:
        assert "教育" in reasons or "获奖" in reasons or "硬凑" in reasons or "勿" in reasons
