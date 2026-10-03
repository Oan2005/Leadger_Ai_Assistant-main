from __future__ import annotations

import os


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _test_environment_enabled() -> bool:
    return os.getenv("TEST_ENV", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_openrouter_api_key() -> str:
    if _test_environment_enabled():
        api_key = os.getenv("TEST_OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "TEST_OPENROUTER_API_KEY is required when TEST_ENV is enabled."
            )
        return api_key

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY or OPENAI_API_KEY is required."
        )
    return api_key
