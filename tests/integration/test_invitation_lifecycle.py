from __future__ import annotations

import hashlib
import os
import uuid
from urllib.parse import parse_qs, urlparse

import psycopg2
from fastapi.testclient import TestClient
from supabase import create_client


def _database_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=15)


def _lookup_invitation(token: str) -> dict[str, object]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, email, company_id, role, expires_at, accepted_at
                FROM invitations
                WHERE token_hash = %s;
                """,
                (token_hash,),
            )
            row = cursor.fetchone()

    assert row is not None
    return {
        "id": row[0],
        "email": row[1],
        "company_id": row[2],
        "role": row[3],
        "expires_at": row[4],
        "accepted_at": row[5],
        "token_hash": token_hash,
    }


def test_real_invitation_lifecycle_in_test_project(
    test_environment,
    captured_invitation_email,
):
    from main import app

    admin_email = os.environ.get("TEST_COMPANY_A_EMAIL")
    admin_password = os.environ.get("TEST_COMPANY_A_PASSWORD")
    company_name = os.environ.get("TEST_COMPANY_A_NAME")
    assert admin_email and admin_password and company_name

    invited_email = f"{admin_email.split('@', 1)[0]}+leadger-{uuid.uuid4().hex}@gmail.com"
    invited_password = "IntegrationTestPassword-2026!"
    client = TestClient(app)
    admin_access_token = None
    invited_user_id = None
    invitation = None

    try:
        login_response = client.post(
            "/signin",
            json={"email": admin_email, "password": admin_password},
        )
        assert login_response.status_code == 200, login_response.text
        admin_access_token = login_response.json()["access_token"]

        admin_identity_response = client.get(
            "/test-current-user",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert admin_identity_response.status_code == 200
        admin_user = admin_identity_response.json()["current_user"]
        company_id = admin_user["company_id"]
        assert admin_user["role"] == "admin"

        invite_response = client.post(
            "/admin/invite",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "email": invited_email,
                "role": "employee",
                "phone": "0000000000",
            },
        )
        assert invite_response.status_code == 200, invite_response.text
        assert invite_response.json()["success"] is True

        message = captured_invitation_email.latest()
        assert message is not None
        assert message.recipient_email == invited_email
        token = parse_qs(urlparse(message.invitation_url).query)["token"][0]

        invitation = _lookup_invitation(token)
        assert invitation["company_id"] == company_id
        assert invitation["email"] == invited_email
        assert invitation["role"] == "employee"
        assert invitation["expires_at"] is not None
        assert invitation["accepted_at"] is None

        validation_response = client.get(
            "/company/invite/validate",
            params={"token": token},
        )
        assert validation_response.status_code == 200, validation_response.text
        assert validation_response.json() == {
            "valid": True,
            "email": invited_email,
            "role": "employee",
            "company_id": company_id,
        }

        invalid_response = client.get(
            "/company/invite/validate",
            params={"token": "invalid-integration-token"},
        )
        assert invalid_response.status_code == 400

        signup_response = client.post(
            "/signup/invited",
            json={
                "token": token,
                "password": invited_password,
                "full_name": "Integration Invitee",
                "email": "attacker@example.test",
                "company_id": "attacker-company",
                "role": "admin",
            },
        )
        assert signup_response.status_code == 200, signup_response.text
        assert signup_response.json()["email"] == invited_email

        test_supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
        invited_login = test_supabase.auth.sign_in_with_password(
            {"email": invited_email, "password": invited_password}
        )
        assert invited_login.user is not None
        assert invited_login.session is not None
        invited_user_id = invited_login.user.id

        with _database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id, company_id, email, role
                    FROM users
                    WHERE user_id = %s;
                    """,
                    (invited_user_id,),
                )
                application_user = cursor.fetchone()

        assert application_user == (
            invited_user_id,
            company_id,
            invited_email,
            "employee",
        )

        accepted_invitation = _lookup_invitation(token)
        assert accepted_invitation["accepted_at"] is not None

        authenticated_identity = client.post(
            "/company/users/me",
            headers={
                "Authorization": f"Bearer {invited_login.session.access_token}"
            },
        )
        assert authenticated_identity.status_code == 200
        assert authenticated_identity.json()["user_id"] == invited_user_id
        assert authenticated_identity.json()["company_id"] == company_id
        assert authenticated_identity.json()["role"] == "employee"

        reused_response = client.post(
            "/signup/invited",
            json={
                "token": token,
                "password": "AnotherPassword-2026!",
                "full_name": "Reuse Attempt",
            },
        )
        assert reused_response.status_code == 400

    finally:
        if invitation is not None or invited_user_id is not None:
            cleanup_client = create_client(
                os.environ["SUPABASE_URL"],
                os.environ["SUPABASE_SERVICE_ROLE_KEY"],
            )
            with _database_connection() as connection:
                with connection.cursor() as cursor:
                    if invited_user_id is not None:
                        cursor.execute(
                            "DELETE FROM users WHERE user_id = %s;",
                            (invited_user_id,),
                        )
                    if invitation is not None:
                        cursor.execute(
                            "DELETE FROM invitations WHERE id = %s;",
                            (invitation["id"],),
                        )
                    else:
                        cursor.execute(
                            """
                            DELETE FROM invitations
                            WHERE email = %s
                            AND accepted_at IS NULL;
                            """,
                            (invited_email,),
                        )
                connection.commit()

            if invited_user_id is not None:
                cleanup_client.auth.admin.delete_user(invited_user_id)
