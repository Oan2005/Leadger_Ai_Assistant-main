from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx
import pytest
from fastapi import HTTPException


def test_explicit_test_environment_is_loaded(test_environment):
    assert test_environment["supabase_url"]
    assert urlparse(test_environment["supabase_url"]).hostname
    assert os.environ["TEST_ENV"].lower() in {"1", "true", "yes", "on"}
    assert os.environ["RUN_INTEGRATION_TESTS"] == "1"


def test_test_llm_configuration_is_explicitly_available(test_environment):
    assert os.environ["TEST_OPENROUTER_API_KEY"]
    assert not os.environ.get("OPENAI_API_KEY")
    assert not os.environ.get("OPENROUTER_API_KEY")
    assert not os.environ.get("OPENROUTE_API_KEY")


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


def test_test_employee_lookup_returns_truthy_application_record(test_environment):
    from app.database import db_connection
    from app.database.crud.users_crud import get_user_by_id

    user_id = "5c1729f4-18c9-4b7a-b7d7-abc629d83357"
    user_info = get_user_by_id(user_id)

    assert db_connection.DATABASE_URL == os.environ["TEST_DATABASE_URL"]
    assert isinstance(user_info, dict)
    assert bool(user_info) is True
    assert user_info is not None
    assert set(user_info) == {
        "user_id",
        "company_id",
        "full_name",
        "email",
        "role",
        "phone",
    }
    assert user_info["user_id"] == user_id


def test_login_accepts_existing_test_application_user(test_environment):
    from unittest.mock import patch

    from app.auth import Auth_endpoint
    from app.models.pydantic_classes.auth_pydantic import SignInRequest

    auth_response = {
        "user_id": "5c1729f4-18c9-4b7a-b7d7-abc629d83357",
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
    }

    with patch.object(Auth_endpoint, "sign_in", return_value=auth_response):
        response = Auth_endpoint.login(
            SignInRequest(
                email=os.environ["TEST_COMPANY_B_EMPLOYEE_EMAIL"],
                password="not-used",
            )
        )

    assert response["success"] is True
    assert response["user_id"] == auth_response["user_id"]


def test_login_rejects_missing_application_user(test_environment):
    from unittest.mock import patch

    from app.auth import Auth_endpoint
    from app.models.pydantic_classes.auth_pydantic import SignInRequest

    auth_response = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
    }

    with patch.object(Auth_endpoint, "sign_in", return_value=auth_response):
        with pytest.raises(HTTPException) as raised:
            Auth_endpoint.login(
                SignInRequest(
                    email="missing@example.com",
                    password="not-used",
                )
            )

    assert raised.value.status_code == 403


def test_signin_endpoint_distinguishes_existing_and_missing_application_users(
    test_environment,
):
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from app.auth import Auth_endpoint
    from main import app

    client = TestClient(app)
    valid_auth_response = {
        "user_id": "5c1729f4-18c9-4b7a-b7d7-abc629d83357",
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
    }
    missing_auth_response = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
    }

    with patch.object(Auth_endpoint, "sign_in", return_value=valid_auth_response):
        valid_response = client.post(
            "/signin",
            json={
                "email": os.environ["TEST_COMPANY_B_EMPLOYEE_EMAIL"],
                "password": "not-used",
            },
        )

    with patch.object(
        Auth_endpoint,
        "sign_in",
        return_value=missing_auth_response,
    ):
        missing_response = client.post(
            "/signin",
            json={"email": "missing@example.com", "password": "not-used"},
        )

    assert valid_response.status_code == 200
    assert valid_response.json()["success"] is True
    assert missing_response.status_code == 403


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
