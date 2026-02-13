"""
LLM Configuration for AG2 Agent System.
Supports xAI Grok via OpenAI-compatible API.
Reads API keys from environment variables (Replit Secrets).
"""

import os
from typing import Any

XAI_BASE_URL = "https://api.x.ai/v1"


def get_llm_config() -> dict[str, Any]:
    """Build LLM config from environment variables.

    Replit Secrets should contain:
        XAI_API_KEY      - xAI/Grok API key (required)
        AG2_MODEL        - model name override (optional, default: grok-3-mini-fast)
    """
    api_key = os.environ.get("XAI_API_KEY", "")
    model = os.environ.get("AG2_MODEL", "grok-3-mini-fast")

    if not api_key:
        raise EnvironmentError(
            "XAI_API_KEY not set. Add it to Replit Secrets "
            "(Tools > Secrets > XAI_API_KEY)."
        )

    config_list = [
        {
            "model": model,
            "api_key": api_key,
            "base_url": XAI_BASE_URL,
        }
    ]

    return {
        "config_list": config_list,
        "temperature": 0.1,
        "timeout": 120,
        "cache_seed": None,
    }


def get_captain_llm_config() -> dict[str, Any]:
    """Higher-capability model config for CaptainAgent orchestration."""
    api_key = os.environ.get("XAI_API_KEY", "")
    captain_model = os.environ.get("AG2_CAPTAIN_MODEL", "grok-3-fast")

    if not api_key:
        raise EnvironmentError("XAI_API_KEY not set.")

    config_list = [
        {
            "model": captain_model,
            "api_key": api_key,
            "base_url": XAI_BASE_URL,
        }
    ]

    return {
        "config_list": config_list,
        "temperature": 0,
        "timeout": 180,
        "cache_seed": None,
    }
