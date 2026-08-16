from app.services.optimized_resume import attach_optimized_resume, build_optimized_resume
from app.services.score_engine import build_evidence, score_resume
from app.services.skill_graph import build_skill_graph_hints, load_skill_graph


def test_skill_graph_loads_and_hints_parent_skill():
    graph = load_skill_graph()
    assert graph.get("by_id")
    hints = build_skill_graph_hints(
        "熟悉 Python 与 pandas 数据处理",
        matched_keywords=["Python"],
        missing_keywords=["SQL"],
        target_position="数据分析师",
    )
    assert hints["hit_skills"]
    assert any(item["type"] == "parent_skill" for item in hints["hints"]) or any(
        item["type"] == "missing_keyword" for item in hints["hints"]
    )


def test_build_optimized_resume_replaces_lines():
    sections = {
        "projects": ["参与数据分析项目，负责数据清洗"],
        "skills": ["Python"],
    }
    items = [
        {
            "section": "经历",
            "original": "参与数据分析项目，负责数据清洗",
            "suggested": "【数据分析师】负责数据清洗：使用 Python 推进核心任务，在 __ 周期内完成 __ 项交付",
            "focus": "STAR",
        }
    ]
    optimized = build_optimized_resume(
        sections,
        items,
        target_position="数据分析师",
        skill_hints=[
            {
                "type": "parent_skill",
                "hit_skill": "Python",
                "suggest_skill": "数据分析",
                "message": "建议补充数据分析",
            }
        ],
    )
    assert optimized["change_count"] >= 1
    assert "数据分析师" in optimized["document_text"]
    assert any("数据清洗" in line for line in optimized["sections"]["projects"])


def test_attach_optimized_resume_on_preview():
    preview = attach_optimized_resume(
        {
            "summary": "测试",
            "items": [
                {
                    "section": "经历",
                    "original": "参与了项目",
                    "suggested": "负责项目落地并产出 __ 份报告",
                    "focus": "量化",
                }
            ],
            "target_position": "产品经理",
            "mode": "offline_star",
        },
        {"projects": ["参与了项目"]},
    )
    assert "optimized_resume" in preview
    assert preview["optimized_resume"]["diffs"]


def test_low_snr_evidence_and_penalty():
    parsed = {
        "raw_text": "实习经历\n参与了很多项目，比较熟悉相关业务\n教育背景\n某大学 本科",
        "sections": {
            "education": ["某大学 本科"],
            "internship": ["参与了很多项目，比较熟悉相关业务"],
            "projects": [],
            "skills": ["沟通"],
            "basic_info": ["张三"],
        },
        "detected_keywords": [],
        "parse_quality": "medium",
        "parse_warnings": [],
    }
    evidence = build_evidence(parsed["sections"], parsed["raw_text"])
    assert evidence["low_snr_zones"]
    assert evidence["evidence_confidence"] < 0.7
    scored = score_resume(parsed, "数据分析师", "需要 Python SQL")
    assert "low_snr_zones" in scored
    assert "evidence_confidence" in scored
