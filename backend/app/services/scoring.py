"""评分编排：组合评分引擎、匹配引擎与建议引擎。"""

from typing import Any

from app.services.match_engine import match_job
from app.services.score_engine import JOB_PROFILES, WEIGHTS, build_evidence, label_for_score, score_resume
from app.services.suggestion_engine import build_diagnosis, build_suggestions

__all__ = [
    "analyze_resume",
    "build_diagnosis",
    "build_suggestions",
    "build_evidence",
    "label_for_score",
    "match_job",
    "JOB_PROFILES",
    "WEIGHTS",
]


def analyze_resume(parsed: dict[str, Any], target_position: str = "", job_description: str = "") -> dict[str, Any]:
    scored = score_resume(parsed, target_position, job_description)
    diagnosis = build_diagnosis(
        scored["scores"],
        parsed.get("sections", {}),
        scored["match_result"],
        scored["parse_warnings"],
        scored["parse_quality"],
        scored["evidence"],
    )
    suggestions = build_suggestions(
        scored["scores"],
        parsed.get("sections", {}),
        scored["match_result"],
        scored["parse_quality"],
        scored["evidence"],
    )
    return {
        **scored,
        "diagnosis": diagnosis,
        "suggestions": suggestions,
    }
