"""双塔/融合器训练脚手架（离线可跑）。

默认：
1) 估计 token IDF
2) 拟合约束融合权重 alpha∈[0,1]：score ≈ α·Rule + (1-α)·Semantic
3) 导出到独立实验目录，不覆盖线上产物。

可选：安装 sentence-transformers 后扩展为真正 SBERT 微调。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "train-biencoder-secret")
os.environ.setdefault("USE_SEMANTIC_MATCH", "true")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings

get_settings.cache_clear()

from app.services.match_engine import match_job
from app.services.semantic_match import clear_semantic_caches, semantic_similarity


def _tokenize_for_idf(text: str) -> list[str]:
    import re

    import jieba

    lowered = text.lower()
    tokens = re.findall(r"[a-z][a-z0-9+.#]{1,24}", lowered)
    tokens.extend(t.strip() for t in jieba.lcut(lowered) if len(t.strip()) >= 2)
    return tokens


def fit_idf(cases: list[dict]) -> dict[str, float]:
    df: Counter[str] = Counter()
    docs = 0
    for case in cases:
        docs += 1
        seen = set(_tokenize_for_idf(f"{case['resume']}\n{case['job']}"))
        for token in seen:
            df[token] += 1
    return {token: math.log((1 + docs) / (1 + count)) + 1.0 for token, count in df.items()}


def _spearman(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0

    def ranks(vals: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: vals[i])
        out = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    deny = math.sqrt(sum((b - my) ** 2 for b in ry))
    if denx <= 1e-9 or deny <= 1e-9:
        return 0.0
    return num / (denx * deny)


def fit_alpha(rows: list[tuple[float, float, float]]) -> float:
    """网格搜索 α∈[0.35, 0.75]，最大化与人工 label 的 Spearman。"""
    labels = [y for y, _, _ in rows]
    best_a, best_rho = 0.55, -1.0
    for step in range(35, 76):
        alpha = step / 100.0
        preds = [alpha * rule + (1.0 - alpha) * sem for _, rule, sem in rows]
        rho = _spearman(labels, preds)
        if rho > best_rho + 1e-9 or (abs(rho - best_rho) <= 1e-9 and abs(alpha - 0.55) < abs(best_a - 0.55)):
            best_rho, best_a = rho, alpha
    return round(best_a, 4)


def main() -> int:
    parser = argparse.ArgumentParser(description="fit IDF and optional rule/semantic blender on a selected split")
    parser.add_argument("--input", type=Path, default=None, help="JSON training split; defaults to group-disjoint train split")
    parser.add_argument("--output-dir", type=Path, default=None, help="separate experiment output directory")
    args = parser.parse_args()
    settings = get_settings()
    cases_path = args.input or (settings.data_dir / "eval" / "match_splits" / "train.json")
    if not cases_path.exists():
        print("missing eval set, run build_match_eval_set.py first")
        return 1
    cases = json.loads(cases_path.read_text(encoding="utf-8")).get("cases") or []
    model_dir = args.output_dir or (settings.data_dir / "models" / "experiments" / "match-train")
    model_dir.mkdir(parents=True, exist_ok=True)

    # 训练时先移除旧 blender，避免自举污染
    blender_path = model_dir / "match_blender.json"
    if blender_path.exists():
        blender_path.unlink()
    clear_semantic_caches()

    idf = fit_idf(cases)
    idf_path = model_dir / "semantic_idf.json"
    idf_path.write_text(json.dumps({"idf": idf, "docs": len(cases)}, ensure_ascii=False), encoding="utf-8")
    clear_semantic_caches()

    rows: list[tuple[float, float, float]] = []
    for case in cases:
        y = float(case["label"]) * 20.0
        os.environ["USE_SEMANTIC_MATCH"] = "false"
        rule = float(match_job(case["resume"], [], "", case["job"], "manual")["score"])
        os.environ["USE_SEMANTIC_MATCH"] = "true"
        clear_semantic_caches()
        sem = float(semantic_similarity(case["resume"], case["job"])["score"])
        rows.append((y, rule, sem))

    alpha = fit_alpha(rows)
    blender_path.write_text(
        json.dumps(
            {
                "type": "alpha_blender",
                "alpha": alpha,
                "trained_on": len(rows),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    clear_semantic_caches()

    mae = sum(abs(alpha * rule + (1 - alpha) * sem - y) for y, rule, sem in rows) / len(rows)
    print("=== train_biencoder (offline scaffold) ===")
    print(f"cases: {len(cases)}")
    print(f"idf tokens: {len(idf)} -> {idf_path}")
    print(f"alpha: {alpha} -> {blender_path}")
    print(f"train MAE(vs label*20): {mae:.2f}")
    print("note: 完整 SBERT 微调请运行 scripts/train_sbert.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
