"""
LLM Configuration for AG2 Agent System.
Supports Groq (GroqCloud) via OpenAI-compatible API.
Reads API keys from environment variables (Replit Secrets).
"""

import os
from typing import Any

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_llm_config() -> dict[str, Any]:
    """Build LLM config from environment variables.

    Replit Secrets should contain:
        GROQ_API_KEY     - Groq API key (required, starts with gsk_)
        AG2_MODEL        - model name override (optional, default: llama-3.3-70b-versatile)
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    model = os.environ.get("AG2_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set. Add it to Replit Secrets "
            "(Tools > Secrets > GROQ_API_KEY)."
        )

    config_list = [
        {
            "model": model,
            "api_key": api_key,
            "base_url": GROQ_BASE_URL,
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
    api_key = os.environ.get("GROQ_API_KEY", "")
    captain_model = os.environ.get("AG2_CAPTAIN_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set.")

    config_list = [
        {
            "model": captain_model,
            "api_key": api_key,
            "base_url": GROQ_BASE_URL,
        }
    ]

    return {
        "config_list": config_list,
        "temperature": 0,
        "timeout": 180,
        "cache_seed": None,
    }
