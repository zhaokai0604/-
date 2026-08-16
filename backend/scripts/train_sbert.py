"""真正微调中文双塔（CosineSimilarityLoss），导出到独立实验目录。

依赖：torch + sentence-transformers（见 requirements-semantic.txt）
若 Windows 智能应用控制拦截 torch DLL，请关闭后重启再跑。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "train-sbert-secret")
# 微调下载基座时可用国内镜像：set HF_ENDPOINT=https://hf-mirror.com
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings

get_settings.cache_clear()


def _check_torch() -> None:
    try:
        import torch  # noqa: F401
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "缺少 torch / sentence-transformers。请先安装 requirements-semantic.txt。"
        ) from exc
    except OSError as exc:
        raise SystemExit(
            "torch 已安装但无法加载 DLL（常见于 Windows 智能应用控制）。"
            "请关闭「智能应用控制」后重启，再重试本脚本。\n"
            f"原始错误: {exc}"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune SBERT on a selected match dataset")
    parser.add_argument("--input", type=Path, default=None, help="JSON training split; defaults to group-disjoint train split")
    parser.add_argument("--output-dir", type=Path, default=None, help="separate experiment output directory")
    parser.add_argument(
        "--base-model",
        default=os.getenv("SEMANTIC_MODEL_NAME", "shibing624/text2vec-base-chinese"),
        help="HuggingFace 基座或本地路径",
    )
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--warmup-steps", type=int, default=10)
    args = parser.parse_args()

    _check_torch()
    from sentence_transformers import InputExample, SentenceTransformer
    from sentence_transformers.sentence_transformer import losses
    from torch.utils.data import DataLoader

    settings = get_settings()
    cases_path = args.input or (settings.data_dir / "eval" / "match_splits" / "train.json")
    if not cases_path.exists():
        print("missing eval set, run build_match_eval_set.py first")
        return 1
    cases = json.loads(cases_path.read_text(encoding="utf-8")).get("cases") or []
    if len(cases) < 8:
        print("need at least 8 labeled pairs")
        return 1

    out_dir = args.output_dir or (settings.data_dir / "models" / "experiments" / "sbert-resume-match-train")
    out_dir.mkdir(parents=True, exist_ok=True)

    examples = [
        InputExample(
            texts=[str(case["resume"])[:1200], str(case["job"])[:800]],
            label=float(case["label"]) / 5.0,
        )
        for case in cases
        if case.get("resume") and case.get("job")
    ]
    print(f"=== train_sbert ===")
    print(f"base: {args.base_model}")
    print(f"pairs: {len(examples)} -> {out_dir}")

    model = SentenceTransformer(args.base_model)
    loader = DataLoader(examples, shuffle=True, batch_size=max(2, args.batch_size))
    train_loss = losses.CosineSimilarityLoss(model)
    model.fit(
        train_objectives=[(loader, train_loss)],
        epochs=max(1, args.epochs),
        warmup_steps=max(0, args.warmup_steps),
        output_path=str(out_dir),
        show_progress_bar=True,
    )

    meta = {
        "base_model": args.base_model,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "pairs": len(examples),
        "loss": "CosineSimilarityLoss",
        "output": str(out_dir),
        "source": str(cases_path),
        "split": "train" if "match_splits" in str(cases_path).replace("\\", "/") else "explicit",
    }
    (out_dir / "train_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved:", out_dir)
    print("hint: set USE_SEMANTIC_MODEL=true and SEMANTIC_MODEL_PATH to this folder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
