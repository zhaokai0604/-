"""语义匹配基线：同义扩展分词向量 + 可选 sentence-transformers + 可选线性融合器。"""

from __future__ import annotations

import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


def semantic_similarity(resume_text: str, job_text: str) -> dict[str, Any]:
    """返回 0~100 语义分与置信度；失败时降级为 0 分并标明 unavailable。"""
    left = (resume_text or "").strip()
    right = (job_text or "").strip()
    if not left or not right:
        return {
            "score": 0.0,
            "confidence": 0.0,
            "backend": "none",
            "available": False,
            "summary": "文本不足，跳过语义匹配。",
        }

    if _use_transformer():
        try:
            score = _transformer_cosine(left, right)
            return {
                "score": round(score * 100, 1),
                "confidence": round(min(0.92, 0.55 + score * 0.4), 2),
                "backend": "sentence_transformers",
                "available": True,
                "summary": f"语义相似度（向量模型）{round(score * 100, 1)}%。",
            }
        except Exception:
            pass

    score = _bow_cosine(left, right)
    # 同义扩展后再算一次，取较高值（缓解 pandas/Python 等表述差）
    expanded = _bow_cosine(_expand_text(left), _expand_text(right))
    score = max(score, expanded)
    return {
        "score": round(score * 100, 1),
        "confidence": round(min(0.88, 0.45 + score * 0.42), 2),
        "backend": "jieba_tf_cosine+synonym",
        "available": True,
        "summary": f"语义相似度（分词+同义扩展）{round(score * 100, 1)}%。",
    }


def fuse_match_scores(rule_score: float, semantic_score: float, *, alpha: float | None = None) -> dict[str, Any]:
    """Final = α·Rule + (1-α)·Semantic；显式 alpha 优先，否则读训练得到的 alpha_blender。"""
    if alpha is None:
        blender = _load_blender()
        if blender and blender.get("alpha") is not None:
            weight = float(blender["alpha"])
            used_blender = True
        else:
            weight = _rule_weight()
            used_blender = False
    else:
        weight = float(alpha)
        used_blender = False

    weight = max(0.0, min(1.0, weight))
    fused = weight * float(rule_score) + (1.0 - weight) * float(semantic_score)
    return {
        "rule_score": round(float(rule_score), 1),
        "semantic_score": round(float(semantic_score), 1),
        "fused_score": round(max(0.0, min(100.0, fused)), 1),
        "alpha": weight,
        "blender": used_blender,
    }


def _use_transformer() -> bool:
    # A model name alone may trigger a network download. Transformer mode is
    # therefore opt-in only when a local, explicitly reviewed artifact path is set.
    return (
        os.getenv("USE_SEMANTIC_MODEL", "false").lower() == "true"
        and bool((os.getenv("SEMANTIC_MODEL_PATH") or "").strip())
    )


def _rule_weight() -> float:
    raw = os.getenv("MATCH_RULE_WEIGHT", "0.65")
    try:
        return float(raw)
    except ValueError:
        return 0.65


def _bow_cosine(left: str, right: str) -> float:
    vec_a = _vectorize(left)
    vec_b = _vectorize(right)
    if not vec_a or not vec_b:
        return 0.0
    dot = 0.0
    for key, value in vec_a.items():
        dot += value * vec_b.get(key, 0.0)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a <= 1e-9 or norm_b <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def _vectorize(text: str) -> dict[str, float]:
    tokens = _tokenize(text)
    if not tokens:
        return {}
    counts: dict[str, float] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0.0) + 1.0
    idf = _load_idf()
    weighted = {key: value * float(idf.get(key, 1.0)) for key, value in counts.items()}
    norm = math.sqrt(sum(v * v for v in weighted.values())) or 1.0
    return {key: value / norm for key, value in weighted.items()}


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens: list[str] = []
    tokens.extend(re.findall(r"[a-z][a-z0-9+.#]{1,24}", lowered))
    try:
        import jieba

        for piece in jieba.lcut(lowered):
            piece = piece.strip()
            if len(piece) >= 2 and re.search(r"[\u4e00-\u9fffA-Za-z]", piece):
                tokens.append(piece)
    except Exception:
        chars = re.findall(r"[\u4e00-\u9fff]", lowered)
        tokens.extend("".join(chars[i : i + 2]) for i in range(max(0, len(chars) - 1)))
    # 同义归一：把别名映射到规范词，同时保留原词
    canon = _synonym_map()
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        root = canon.get(token)
        if root and root != token:
            expanded.append(root)
    return expanded[:1000]


def _expand_text(text: str) -> str:
    canon = _synonym_map()
    lowered = text.lower()
    extras: list[str] = []
    for alias, root in canon.items():
        if alias in lowered and root not in lowered:
            extras.append(root)
    if not extras:
        return text
    return text + "\n" + " ".join(sorted(set(extras)))


@lru_cache(maxsize=1)
def _synonym_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    path = settings.data_dir / "lexicon" / "skill_synonyms.json"
    if not path.exists():
        return mapping
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return mapping
    for root, aliases in payload.items():
        root_key = str(root).lower().strip()
        if not root_key:
            continue
        mapping[root_key] = root_key
        if isinstance(aliases, list):
            for alias in aliases:
                key = str(alias).lower().strip()
                if key:
                    mapping[key] = root_key
    # 技能图谱别名补充
    graph_path = settings.data_dir / "skill_graph.json"
    if graph_path.exists():
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        for node in graph.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            name = str(node.get("name") or "").lower().strip()
            if name:
                mapping[name] = name
            for alias in node.get("aliases") or []:
                key = str(alias).lower().strip()
                if key and name:
                    mapping[key] = name
    return mapping


@lru_cache(maxsize=1)
def _load_idf() -> dict[str, float]:
    path = Path(os.getenv("SEMANTIC_IDF_PATH", "")) if os.getenv("SEMANTIC_IDF_PATH") else settings.data_dir / "models" / "semantic_idf.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in (payload.get("idf") or {}).items()}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _load_blender() -> dict[str, float] | None:
    # Fitted weights are experiment artifacts. Never activate them merely
    # because a local model file happens to exist in the project tree.
    configured_path = (os.getenv("SEMANTIC_BLENDER_PATH") or "").strip()
    if not configured_path:
        return None
    path = Path(configured_path).expanduser()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "alpha" in payload:
            return {"alpha": float(payload["alpha"])}
        # 兼容旧版线性系数：折算为近似 alpha
        w_rule = float(payload.get("w_rule", 0.65))
        w_sem = float(payload.get("w_semantic", 0.35))
        total = w_rule + w_sem
        if total <= 1e-9:
            return None
        return {"alpha": max(0.0, min(1.0, w_rule / total))}
    except Exception:
        return None


def clear_semantic_caches() -> None:
    _synonym_map.cache_clear()
    _load_idf.cache_clear()
    _load_blender.cache_clear()
    _load_sentence_model.cache_clear()


def _resolve_sentence_model_name() -> str:
    """Only an explicit path may activate a local experiment artifact."""
    env_path = (os.getenv("SEMANTIC_MODEL_PATH") or "").strip()
    if env_path:
        return env_path
    return os.getenv("SEMANTIC_MODEL_NAME", "shibing624/text2vec-base-chinese")


@lru_cache(maxsize=1)
def _load_sentence_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_resolve_sentence_model_name())


def _transformer_cosine(left: str, right: str) -> float:
    model = _load_sentence_model()
    embeddings = model.encode([left[:2000], right[:2000]], normalize_embeddings=True)
    score = float(embeddings[0] @ embeddings[1])
    return max(0.0, min(1.0, score))
