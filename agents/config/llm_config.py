"""
LLM Configuration for AG2 Agent System.
Supports OpenAI, Anthropic, and local models.
Reads API keys from environment variables (Replit Secrets).
"""

import os
from typing import Any


def get_llm_config() -> dict[str, Any]:
    """Build LLM config from environment variables.

    Replit Secrets should contain:
        OPENAI_API_KEY   - for GPT models (default)
        ANTHROPIC_API_KEY - for Claude models (optional)
        AG2_MODEL        - model name override (optional)
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("AG2_MODEL", "gpt-4o-mini")

    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY not set. Add it to Replit Secrets "
            "(Tools > Secrets > OPENAI_API_KEY)."
        )

    config_list = [
        {
            "model": model,
            "api_key": api_key,
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
    api_key = os.environ.get("OPENAI_API_KEY", "")
    captain_model = os.environ.get("AG2_CAPTAIN_MODEL", "gpt-4o")

    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set.")

    config_list = [
        {
            "model": captain_model,
            "api_key": api_key,
        }
    ]

    return {
        "config_list": config_list,
        "temperature": 0,
        "timeout": 180,
        "cache_seed": None,
    }
