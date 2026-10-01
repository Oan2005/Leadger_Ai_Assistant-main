from __future__ import annotations

import os
import uuid

import psycopg2
import pytest
from fastapi.testclient import TestClient


def _database_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=15)


def _require_isolated_pinecone():
    if not os.getenv("TEST_PINECONE_API_KEY"):
        pytest.skip(
            "TEST_PINECONE_API_KEY is not configured. Normal signup creates a "
            "namespace in Pinecone and cannot safely run against production."
        )
    if not os.getenv("TEST_PINECONE_INDEX"):
        pytest.skip(
            "TEST_PINECONE_INDEX is not configured. Normal signup uses the "
            "hard-coded production index and cannot safely run."
        )


def test_real_authentication_lifecycle_in_test_project(test_environment):
    _require_isolated_pinecone()

    from main import app

    email = f"leadger-auth-{uuid.uuid4().hex}@gmail.com"
    password = "IntegrationAuthPassword-2026!"
    company_name = f"Integration Company {uuid.uuid4().hex[:12]}"
    namespace = f"leadger-auth-{uuid.uuid4().hex}"
    client = TestClient(app)
    auth_user_id = None
    company_id = None

    try:
        signup = client.post(
            "/signup",
            json={
                "company_name": company_name,
                "full_name": "Integration Admin",
                "email": email,
                "password": password,
                "namespace": namespace,
                "phone": "0000000000",
            },
        )
        assert signup.status_code == 200, signup.text
        signup_data = signup.json()["data"]
        auth_user_id = signup_data["user_id"]
        company_id = signup_data["company_id"]
        assert signup_data["email"] == email
        assert signup_data["role"] == "admin"

        with _database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id, company_id, email, role
                    FROM users
                    WHERE user_id = %s;
                    """,
                    (auth_user_id,),
                )
                application_user = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT company_id, company_name, namespace
                    FROM companies
                    WHERE company_id = %s;
                    """,
                    (company_id,),
                )
                company = cursor.fetchone()

        assert application_user == (auth_user_id, company_id, email, "admin")
        assert company == (company_id, company_name, namespace)

        signin = client.post(
            "/signin",
            json={"email": email, "password": password},
        )
        assert signin.status_code == 200, signin.text
        session = signin.json()
        assert session["user_id"] == auth_user_id
        assert session["access_token"]
        assert session["refresh_token"]

        identity = client.post(
            "/company/users/me",
            headers={"Authorization": f"Bearer {session['access_token']}"},
        )
        assert identity.status_code == 200
        assert identity.json()["user_id"] == auth_user_id
        assert identity.json()["company_id"] == company_id
        assert identity.json()["role"] == "admin"
        assert identity.json()["email"] == email

        invalid_password = client.post(
            "/signin",
            json={"email": email, "password": "WrongPassword-2026!"},
        )
        assert invalid_password.status_code == 401

        nonexistent = client.post(
            "/signin",
            json={
                "email": f"does-not-exist-{uuid.uuid4().hex}@gmail.com",
                "password": password,
            },
        )
        assert nonexistent.status_code == 401

        duplicate = client.post(
            "/signup",
            json={
                "company_name": f"Duplicate {uuid.uuid4().hex}",
                "full_name": "Duplicate Attempt",
                "email": email,
                "password": password,
                "namespace": f"duplicate-{uuid.uuid4().hex}",
                "phone": "0000000000",
            },
        )
        assert duplicate.status_code != 200

        invalid_token = client.post(
            "/company/users/me",
            headers={"Authorization": "Bearer invalid-integration-token"},
        )
        assert invalid_token.status_code == 401

        missing_auth = client.post("/company/users/me")
        assert missing_auth.status_code == 401

        logout = client.post(
            "/logout",
            headers={"Authorization": f"Bearer {session['access_token']}"},
        )
        assert logout.status_code == 200
    finally:
        if auth_user_id or company_id:
            from supabase import create_client

            admin = create_client(
                os.environ["SUPABASE_URL"],
                os.environ["SUPABASE_SERVICE_ROLE_KEY"],
            )
            with _database_connection() as connection:
                with connection.cursor() as cursor:
                    if auth_user_id:
                        cursor.execute(
                            "DELETE FROM users WHERE user_id = %s;",
                            (auth_user_id,),
                        )
                    if company_id:
                        cursor.execute(
                            "DELETE FROM companies WHERE company_id = %s;",
                            (company_id,),
                        )
                connection.commit()
            if auth_user_id:
                admin.auth.admin.delete_user(auth_user_id)
