import json

from app.services import semantic_match
from app.services.match_engine import match_job
from app.services.semantic_match import clear_semantic_caches, fuse_match_scores, semantic_similarity
from app.services.teacher_training import build_training_task_from_issue


def test_semantic_similarity_positive_for_aligned_texts():
    score = semantic_similarity(
        "使用 Python 与 SQL 完成数据分析与可视化",
        "数据分析师要求 Python SQL 可视化",
    )
    assert score["available"] is True
    assert score["score"] > 20


def test_fuse_match_scores():
    # 显式 alpha 不受已训练 blender 影响
    fused = fuse_match_scores(80, 40, alpha=0.65)
    assert fused["fused_score"] == 66.0
    assert fused["rule_score"] == 80
    assert fused["semantic_score"] == 40
    assert fused["blender"] is False


def test_fitted_blender_requires_explicit_path(monkeypatch, tmp_path):
    artifact = tmp_path / "match_blender.json"
    artifact.write_text(json.dumps({"alpha": 0.01}), encoding="utf-8")
    monkeypatch.delenv("SEMANTIC_BLENDER_PATH", raising=False)
    clear_semantic_caches()
    default = fuse_match_scores(80, 40)
    assert default["alpha"] == 0.65
    assert default["blender"] is False

    monkeypatch.setenv("SEMANTIC_BLENDER_PATH", str(artifact))
    clear_semantic_caches()
    explicit = fuse_match_scores(80, 40)
    assert explicit["alpha"] == 0.01
    assert explicit["blender"] is True
    monkeypatch.delenv("SEMANTIC_BLENDER_PATH", raising=False)
    clear_semantic_caches()


def test_local_transformer_artifact_requires_explicit_path(monkeypatch):
    monkeypatch.delenv("SEMANTIC_MODEL_PATH", raising=False)
    monkeypatch.setenv("SEMANTIC_MODEL_NAME", "base-model")
    assert semantic_match._resolve_sentence_model_name() == "base-model"


def test_match_job_hybrid_fields(monkeypatch):
    monkeypatch.setenv("USE_SEMANTIC_MATCH", "true")
    result = match_job(
        "后端实习：FastAPI 接口开发，MySQL 与 Redis",
        [],
        "后端开发",
        "要求 Python、接口、MySQL、Redis",
        "manual",
    )
    assert "rule_score" in result
    assert "semantic_score" in result
    assert result["match_backend"].startswith("semantic_primary") or result["match_backend"] == "rules_fallback"
    if result["semantic_score"]:
        assert result["score"] == round(result["semantic_score"])
        assert result["rule_role"] == "evidence_and_guardrail"
    assert result["score"] >= 30


def test_match_job_can_disable_semantic(monkeypatch):
    monkeypatch.setenv("USE_SEMANTIC_MATCH", "false")
    result = match_job(
        "后端实习：FastAPI 接口开发，MySQL 与 Redis",
        [],
        "后端开发",
        "要求 Python、接口、MySQL、Redis",
        "manual",
    )
    assert result["match_backend"] == "rules_fallback"
    assert result["semantic_score"] == 0


def test_hard_education_constraint_blocks_semantic_ranking(monkeypatch):
    monkeypatch.setenv("USE_SEMANTIC_MATCH", "true")
    result = match_job(
        "教育背景\n某职业学院 专科\n技能\nPython",
        [],
        "数据分析师",
        "本科及以上，要求 Python 和 SQL",
        "manual",
        sections={"education": ["某职业学院 专科"], "skills": ["Python"]},
        structured={"education": [{"raw": "某职业学院 专科"}]},
    )
    assert result["hard_constraint_blocked"] is True
    assert result["hard_constraints"][0]["status"] == "fail"
    assert result["match_backend"] == "rules_blocked"
    assert result["semantic_score"] == 0


def test_training_task_from_quant_issue():
    task = build_training_task_from_issue(
        "项目缺少量化指标，建议补充提升比例",
        class_name="软件2201",
        affected_count=8,
        total_records=10,
    )
    assert "量化" in task["title"]
    assert task["coverage_percent"] == 80.0
    assert "班级训练任务" in task["student_message"]
    assert "不包含任何学生简历正文" in task["privacy_note"]
