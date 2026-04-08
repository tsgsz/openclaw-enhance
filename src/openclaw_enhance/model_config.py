import json
from pathlib import Path
from typing import Any

MODEL_PRICING: dict[str, list[str]] = {
    "cheap": [
        "gpt-4o-mini",
        "claude-3-haiku",
        "gemini-2.0-flash",
        "deepseek-chat",
        "qwen-2.5-coder-27b-instruct",
    ],
    "mid": [
        "gpt-4o",
        "claude-3.5-sonnet",
        "o3-mini",
        "gemini-2.5-pro",
    ],
    "premium": [
        "claude-opus-4-6",
        "o1",
        "gpt-4.5",
    ],
}

_MODEL_TO_TIER: dict[str, str] = {
    tier: tier for tier in MODEL_PRICING for tier_model in MODEL_PRICING[tier] for tier in [tier]
}


def _get_openclaw_config() -> dict[str, Any]:
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def get_openclaw_models() -> list[dict[str, Any]]:
    config = _get_openclaw_config()
    models: list[dict[str, Any]] = []

    providers = config.get("models", {}).get("providers", {})
    for provider_name, provider_config in providers.items():
        for model in provider_config.get("models", []):
            model_with_provider = dict(model)
            model_with_provider["provider"] = provider_name
            models.append(model_with_provider)

    return models


def get_available_providers() -> list[str]:
    config = _get_openclaw_config()
    providers = config.get("models", {}).get("providers", {})
    return list(providers.keys())


def infer_model_tier(model_id: str) -> str | None:
    if model_id in _MODEL_TO_TIER:
        return _MODEL_TO_TIER[model_id]

    for tier, models in MODEL_PRICING.items():
        for tier_model in models:
            if model_id.endswith(tier_model) or tier_model in model_id:
                return tier

    return None
