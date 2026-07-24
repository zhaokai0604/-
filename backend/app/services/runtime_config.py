import json
from pathlib import Path
from typing import Any

from app.core.config import settings


AI_PROVIDER_OPTIONS = {"deepseek", "openai_compatible"}


def load_runtime_config() -> dict[str, Any]:
    from app.services.config_cache import load_runtime_config_cached

    return load_runtime_config_cached()


def get_ai_runtime_config() -> dict[str, Any]:
    config = load_runtime_config().get("ai", {})
    if not isinstance(config, dict):
        config = {}
    provider = str(config["provider"] if "provider" in config else "deepseek").strip() or "deepseek"
    if provider not in AI_PROVIDER_OPTIONS:
        provider = "deepseek"
    api_url = str(config["api_url"] if "api_url" in config else settings.deepseek_api_url).strip()
    model = str(config["model"] if "model" in config else settings.deepseek_model).strip()
    api_key = str(config["api_key"] if "api_key" in config else settings.deepseek_api_key).strip()
    return {
        "provider": provider,
        "api_url": api_url,
        "model": model,
        "api_key": api_key,
        "api_key_configured": bool(api_key),
        "api_key_masked": _mask_secret(api_key),
        "using_local_override": any(key in config for key in ["provider", "api_url", "model", "api_key"]),
    }


def update_ai_runtime_config(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_config = load_runtime_config()
    ai_config = runtime_config.get("ai", {})
    if not isinstance(ai_config, dict):
        ai_config = {}

    provider = str(payload.get("provider") or ai_config.get("provider") or "deepseek").strip() or "deepseek"
    if provider not in AI_PROVIDER_OPTIONS:
        raise ValueError("provider must be deepseek or openai_compatible")

    api_url = str(payload.get("api_url") or ai_config.get("api_url") or settings.deepseek_api_url).strip()
    if not api_url:
        raise ValueError("api_url is required")

    model = str(payload.get("model") or ai_config.get("model") or settings.deepseek_model).strip()
    if not model:
        raise ValueError("model is required")

    next_config = {
        "provider": provider,
        "api_url": api_url,
        "model": model,
    }

    api_key = str(payload.get("api_key") or "").strip()
    clear_api_key = bool(payload.get("clear_api_key"))
    if clear_api_key:
        next_config["api_key"] = ""
    elif api_key:
        next_config["api_key"] = api_key
    elif "api_key" in ai_config:
        next_config["api_key"] = str(ai_config.get("api_key") or "")

    runtime_config["ai"] = next_config
    path = _runtime_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(runtime_config, ensure_ascii=False, indent=2), encoding="utf-8")
    from app.services.config_cache import invalidate_runtime_config_cache

    invalidate_runtime_config_cache()
    return get_ai_runtime_config()


def _runtime_config_path() -> Path:
    return settings.data_dir / "system_config.json"


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def get_score_runtime_config() -> dict[str, Any]:
    from app.services.score_engine import WEIGHT_TEMPLATES

    config = load_runtime_config().get("score", {})
    if not isinstance(config, dict):
        config = {}
    active_template = str(config.get("active_template") or "default").strip() or "default"
    templates = config.get("templates") if isinstance(config.get("templates"), dict) else {}
    merged = {**WEIGHT_TEMPLATES, **templates}
    return {
        "active_template": active_template if active_template in merged else "default",
        "available_templates": list(merged.keys()),
        "templates": merged,
        "using_local_override": bool(templates) or "active_template" in config,
    }


def update_score_runtime_config(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.score_engine import WEIGHTS

    runtime_config = load_runtime_config()
    score_config = runtime_config.get("score", {})
    if not isinstance(score_config, dict):
        score_config = {}

    active_template = str(payload.get("active_template") or score_config.get("active_template") or "default").strip() or "default"
    templates = score_config.get("templates") if isinstance(score_config.get("templates"), dict) else {}
    if isinstance(payload.get("templates"), dict):
        for name, weights in payload["templates"].items():
            if not isinstance(weights, dict):
                continue
            normalized = {key: float(weights[key]) for key in WEIGHTS if key in weights}
            if normalized:
                total = sum(normalized.values())
                if total > 0:
                    templates[name] = {key: round(value / total, 4) for key, value in normalized.items()}

    score_config["active_template"] = active_template
    score_config["templates"] = templates
    runtime_config["score"] = score_config
    path = _runtime_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(runtime_config, ensure_ascii=False, indent=2), encoding="utf-8")
    from app.services.config_cache import invalidate_runtime_config_cache

    invalidate_runtime_config_cache()
    return get_score_runtime_config()
