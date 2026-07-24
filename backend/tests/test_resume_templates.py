from app.services.resume_template_engine import list_template_catalog, recommend_resume_templates


def test_recommend_resume_templates_for_data_role():
    result = recommend_resume_templates(
        target_position="数据分析师",
        weight_template="数据分析",
        sections={"projects": ["Python 数据分析项目"], "skills": ["Python", "SQL"]},
        missing_keywords=["Tableau"],
    )

    assert result["templates"]
    assert result["templates"][0]["match_score"] >= 1
    assert result["templates"][0]["sections"]


def test_list_template_catalog():
    catalog = list_template_catalog()
    assert len(catalog) >= 3
    assert catalog[0]["id"]
