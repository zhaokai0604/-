from app.services.score_engine import resolve_weights, score_resume


def test_resolve_weights_uses_job_profile_template():
    weights, name = resolve_weights("数据分析")
    assert name == "数据分析"
    assert weights["job_match"] > weights["format_standardization"]


def test_score_resume_includes_weight_template():
    parsed = {
        "raw_text": "前端开发 Vue JavaScript 项目经验",
        "sections": {
            "basic_info": ["李四"],
            "education": ["软件工程"],
            "internship": ["前端实习 Vue 项目"],
            "projects": ["后台管理系统"],
            "skills": ["Vue", "JavaScript"],
        },
        "detected_keywords": ["vue", "javascript"],
        "parse_quality": "high",
        "parse_warnings": [],
    }
    result = score_resume(parsed, "前端开发", "Vue React JavaScript")
    assert result["weight_template"] in {"前端开发", "default", "后端开发"}
