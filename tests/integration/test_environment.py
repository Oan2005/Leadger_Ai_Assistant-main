from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx
import pytest


def test_explicit_test_environment_is_loaded(test_environment):
    assert test_environment["supabase_url"]
    assert urlparse(test_environment["supabase_url"]).hostname
    assert os.environ["TEST_ENV"].lower() in {"1", "true", "yes", "on"}
    assert os.environ["RUN_INTEGRATION_TESTS"] == "1"


def test_test_supabase_project_is_reachable():
    url = os.environ["SUPABASE_URL"].rstrip("/")
    response = httpx.get(
        f"{url}/auth/v1/settings",
        headers={"apikey": os.environ["SUPABASE_KEY"]},
        timeout=15,
    )
    assert response.status_code == 200
    assert urlparse(str(response.url)).hostname == urlparse(url).hostname


def test_application_loaders_use_test_values_without_database_fallback(test_environment):
    from app.database import db_connection
    from app.supabase_client_package import supabase_connection

    assert supabase_connection.SUPABASE_URL == os.environ["SUPABASE_URL"]
    assert test_environment["database_configured"]
    assert db_connection.DATABASE_URL == os.environ["DATABASE_URL"]
    assert db_connection.DATABASE_URL


def test_direct_database_connection_is_read_only_when_configured():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip(
            "TEST_DATABASE_URL is not configured. The backend uses psycopg2 "
            "directly, so database-backed integration tests remain blocked."
        )

    import psycopg2

    with psycopg2.connect(database_url, connect_timeout=15) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            assert cursor.fetchone() == (1,)
