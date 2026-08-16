"""评测关键词规则 vs 语义融合基线（Spearman / 分档准确）。"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "eval-match-secret")
os.environ.setdefault("USE_SEMANTIC_MATCH", "true")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings

get_settings.cache_clear()

from app.services.match_engine import match_job
from app.services.semantic_match import semantic_similarity


def spearman(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0

    def rank(values: list[float]) -> list[float]:
        ordered = sorted((v, i) for i, v in enumerate(values))
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and ordered[j + 1][0] == ordered[i][0]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[ordered[k][1]] = avg
            i = j + 1
        return ranks

    rx, ry = rank(xs), rank(ys)
    mean_x = sum(rx) / n
    mean_y = sum(ry) / n
    num = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry))
    den_x = math.sqrt(sum((a - mean_x) ** 2 for a in rx))
    den_y = math.sqrt(sum((b - mean_y) ** 2 for b in ry))
    if den_x <= 1e-9 or den_y <= 1e-9:
        return 0.0
    return num / (den_x * den_y)


def main() -> int:
    cases_path = get_settings().data_dir / "eval" / "match_cases.json"
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    labels: list[float] = []
    rule_scores: list[float] = []
    semantic_scores: list[float] = []
    fused_scores: list[float] = []

    print("=== 匹配基线评测 ===")
    for case in cases:
        label = float(case["label"])
        # 强制仅规则
        os.environ["USE_SEMANTIC_MATCH"] = "false"
        rule_only = match_job(case["resume"], [], case.get("job", "").split("，")[0], case["job"], "manual")
        # 语义融合
        os.environ["USE_SEMANTIC_MATCH"] = "true"
        hybrid = match_job(case["resume"], [], case.get("job", "").split("，")[0], case["job"], "manual")
        sem = semantic_similarity(case["resume"], case["job"])
        labels.append(label)
        rule_scores.append(float(rule_only["score"]))
        semantic_scores.append(float(sem["score"]))
        fused_scores.append(float(hybrid["score"]))
        print(
            f"{case['id']}: label={label} rule={rule_only['score']} "
            f"semantic={sem['score']} fused={hybrid['score']} ({case.get('note', '')})"
        )

    sp_rule = spearman(labels, rule_scores)
    sp_sem = spearman(labels, semantic_scores)
    sp_fused = spearman(labels, fused_scores)
    print("---")
    print(f"Spearman(label, rule)     = {sp_rule:.4f}")
    print(f"Spearman(label, semantic) = {sp_sem:.4f}")
    print(f"Spearman(label, fused)    = {sp_fused:.4f}")
    lift = sp_fused - sp_rule
    print(f"Fused vs Rule lift        = {lift:+.4f}")
    print(f"cases                     = {len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
