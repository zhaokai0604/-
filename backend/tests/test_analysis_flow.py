"""Integration tests for analyze orchestration."""

from app.services.scoring import analyze_resume


def test_analyze_resume_produces_diagnosis_and_suggestions():
    parsed = {
        "raw_text": "李四\n前端开发\nVue React JavaScript\n负责组件开发与接口联调",
        "sections": {
            "basic_info": ["李四"],
            "education": ["软件工程 本科"],
            "internship": ["前端实习：使用 Vue 开发后台页面"],
            "projects": ["个人博客项目"],
            "skills": ["Vue", "JavaScript", "CSS"],
        },
        "detected_keywords": ["vue", "javascript"],
        "parse_quality": "medium",
        "parse_warnings": [],
    }
    result = analyze_resume(parsed, "前端开发", "熟悉 Vue 和 JavaScript")
    assert result["total_score"] >= 0
    assert isinstance(result["diagnosis"], list)
    assert len(result["diagnosis"]) >= 1
    assert isinstance(result["suggestions"], list)
    assert len(result["suggestions"]) >= 1
    assert "match_result" in result
