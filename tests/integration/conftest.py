from __future__ import annotations

import os
import importlib
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest
from dotenv import dotenv_values

from app.features.invitation.email_provider import test_email_provider

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_ENV_FILE = PROJECT_ROOT / ".env.test"


def _is_enabled(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def load_test_environment() -> dict[str, str | None]:
    """Load only the explicitly selected test environment.

    The application uses canonical names such as SUPABASE_URL and
    DATABASE_URL. .env.test keeps test values namespaced with TEST_ so a
    normal application process cannot select them accidentally.
    """
    if not _is_enabled(os.getenv("TEST_ENV")):
        raise RuntimeError(
            "Integration tests require TEST_ENV=true. "
            "The test environment was not explicitly enabled."
        )
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        raise RuntimeError(
            "Integration tests require RUN_INTEGRATION_TESTS=1. "
            "Refusing to run without an explicit opt-in."
        )
    if not TEST_ENV_FILE.is_file():
        raise RuntimeError(f"Missing test environment file: {TEST_ENV_FILE}")

    values = dotenv_values(TEST_ENV_FILE)
    required = (
        "TEST_SUPABASE_URL",
        "TEST_SUPABASE_KEY",
        "TEST_SUPABASE_SERVICE_ROLE_KEY",
        "TEST_OPENROUTER_API_KEY",
    )
    missing = [name for name in required if not values.get(name)]
    if missing:
        raise RuntimeError(
            "Missing required test environment variables: " + ", ".join(missing)
        )

    test_url = values["TEST_SUPABASE_URL"]
    parsed_test_url = urlparse(test_url or "")
    if parsed_test_url.scheme != "https" or not parsed_test_url.hostname:
        raise RuntimeError("TEST_SUPABASE_URL must be an HTTPS Supabase URL.")

    production_values = dotenv_values(PROJECT_ROOT / ".env")
    production_url = production_values.get("SUPABASE_URL")
    if production_url and urlparse(production_url).hostname == parsed_test_url.hostname:
        raise RuntimeError(
            "TEST_SUPABASE_URL matches the production Supabase project. "
            "Refusing to run integration tests."
        )

    # Clear inherited canonical values first so dotenv's normal non-override
    # behavior cannot accidentally select .env or the caller's environment.
    for name in (
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENROUTE_API_KEY",
    ):
        os.environ.pop(name, None)

    os.environ["SUPABASE_URL"] = values["TEST_SUPABASE_URL"] or ""
    os.environ["SUPABASE_KEY"] = values["TEST_SUPABASE_KEY"] or ""
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = (
        values["TEST_SUPABASE_SERVICE_ROLE_KEY"] or ""
    )
    os.environ["TEST_OPENROUTER_API_KEY"] = (
        values["TEST_OPENROUTER_API_KEY"] or ""
    )
    if values.get("TEST_DATABASE_URL"):
        os.environ["DATABASE_URL"] = values["TEST_DATABASE_URL"] or ""
    else:
        # Keep dotenv's default non-override behavior from reloading the
        # production DATABASE_URL when application modules are imported.
        os.environ["DATABASE_URL"] = ""

    # Some test modules import the application during collection, before this
    # session fixture runs. Refresh the cached database configuration after
    # the TEST environment has been installed.
    database_module = sys.modules.get("app.database.db_connection")
    if database_module is not None:
        importlib.reload(database_module)

    return {
        "supabase_url": os.environ["SUPABASE_URL"],
        "database_configured": bool(os.environ.get("DATABASE_URL")),
    }


@pytest.fixture(scope="session", autouse=True)
def test_environment() -> dict[str, str | None]:
    environment = load_test_environment()
    test_email_provider.clear()
    return environment


@pytest.fixture
def captured_invitation_email():
    test_email_provider.clear()
    yield test_email_provider
    test_email_provider.clear()
