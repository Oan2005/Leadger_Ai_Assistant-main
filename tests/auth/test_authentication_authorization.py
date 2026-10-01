import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.auth import Auth_endpoint, user_auth
from app.auth.auth_exceptions import InvalidCredentialsError
from app.auth.sign_in_workflow import SignInRequest, sign_in
from app.models.pydantic_classes.auth_pydantic import (
    InvitedSignupRequest,
    SignInRequest as EndpointSignInRequest,
    SignUpRequest,
)
from app.routes import analysis_metrics_route, users_route


class AuthDependencyTests(unittest.TestCase):
    def user(self, user_id="user-a"):
        return SimpleNamespace(id=user_id, email="person@example.com")

    def test_get_current_user_accepts_valid_token(self):
        response = SimpleNamespace(user=self.user())
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid-token",
        )

        with patch.object(
            user_auth.Supabase_client.auth,
            "get_user",
            return_value=response,
        ) as get_user:
            result = user_auth.get_current_user(credentials)

        self.assertIs(result, response.user)
        get_user.assert_called_once_with("valid-token")

    def test_get_current_user_rejects_provider_response_without_user(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-token",
        )

        with patch.object(
            user_auth.Supabase_client.auth,
            "get_user",
            return_value=SimpleNamespace(user=None),
        ):
            with self.assertRaises(HTTPException) as raised:
                user_auth.get_current_user(credentials)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "Invalid authentication")

    def test_get_current_user_maps_auth_provider_failure_to_401(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="expired-token",
        )

        with patch.object(
            user_auth.Supabase_client.auth,
            "get_user",
            side_effect=RuntimeError("provider unavailable"),
        ):
            with self.assertRaises(HTTPException) as raised:
                user_auth.get_current_user(credentials)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "Invalid or expired token")

    def test_missing_bearer_credentials_are_rejected_by_http_bearer(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(user_auth.security(SimpleNamespace(headers={})))

        self.assertEqual(raised.exception.status_code, 401)

    def test_role_dependencies_match_current_role_rules(self):
        users = {
            "admin": self.user("admin-user"),
            "hr": self.user("hr-user"),
            "employee": self.user("employee-user"),
        }

        with patch.object(
            user_auth,
            "get_user_role",
            side_effect=lambda user_id: {
                "admin-user": "admin",
                "hr-user": "hr",
                "employee-user": "employee",
            }[user_id],
        ):
            self.assertIs(
                user_auth.require_admin(users["admin"]),
                users["admin"],
            )
            self.assertIs(user_auth.require_hr(users["hr"]), users["hr"])
            self.assertIs(
                user_auth.require_hr_admin(users["admin"]),
                users["admin"],
            )
            self.assertIs(
                user_auth.require_hr_admin(users["hr"]),
                users["hr"],
            )

            for dependency in (user_auth.require_admin, user_auth.require_hr):
                with self.assertRaises(HTTPException) as raised:
                    dependency(users["employee"])
                self.assertEqual(raised.exception.status_code, 403)

            with self.assertRaises(HTTPException) as raised:
                user_auth.require_admin(users["hr"])
            self.assertEqual(raised.exception.status_code, 403)

            with self.assertRaises(HTTPException) as raised:
                user_auth.require_hr(users["admin"])
            self.assertEqual(raised.exception.status_code, 403)

            with self.assertRaises(HTTPException) as raised:
                user_auth.require_hr_admin(users["employee"])
            self.assertEqual(raised.exception.status_code, 403)

    def test_role_lookup_failure_is_not_authorized(self):
        with patch.object(
            user_auth,
            "get_user_role",
            return_value={"error": "Unable to retrieve user role."},
        ):
            with self.assertRaises(HTTPException) as raised:
                user_auth.require_admin(self.user())

        self.assertEqual(raised.exception.status_code, 403)


class LoginTests(unittest.TestCase):
    def request(self):
        return SignInRequest(
            email="person@example.com",
            password="test-password",
        )

    def test_sign_in_returns_session_tokens_for_valid_credentials(self):
        response = SimpleNamespace(
            session=SimpleNamespace(
                access_token="access-token",
                refresh_token="refresh-token",
            ),
            user=SimpleNamespace(
                id="user-a",
                email="person@example.com",
            ),
        )

        with patch(
            "app.auth.sign_in_workflow.Supabase_client.auth.sign_in_with_password",
            return_value=response,
        ):
            result = sign_in(self.request())

        self.assertEqual(result["user_id"], "user-a")
        self.assertEqual(result["email"], "person@example.com")
        self.assertEqual(result["access_token"], "access-token")
        self.assertEqual(result["refresh_token"], "refresh-token")

    def test_sign_in_rejects_missing_session_or_user(self):
        response = SimpleNamespace(session=None, user=None)

        with patch(
            "app.auth.sign_in_workflow.Supabase_client.auth.sign_in_with_password",
            return_value=response,
        ):
            with self.assertRaises(InvalidCredentialsError):
                sign_in(self.request())

    def test_login_returns_clean_response_for_application_user(self):
        auth_result = {
            "user_id": "user-a",
            "access_token": "access-token",
            "refresh_token": "refresh-token",
        }
        app_user = {"user_id": "user-a", "full_name": "Person"}

        with patch.object(Auth_endpoint, "sign_in", return_value=auth_result), patch.object(
            Auth_endpoint,
            "get_user_by_id",
            return_value=app_user,
        ):
            result = Auth_endpoint.login(self.request())

        self.assertEqual(result["success"], True)
        self.assertEqual(result["message"], "Welcome Person")
        self.assertEqual(result["access_token"], "access-token")
        self.assertNotIn("password", result)

    def test_login_maps_invalid_credentials_to_401(self):
        with patch.object(
            Auth_endpoint,
            "sign_in",
            side_effect=InvalidCredentialsError("bad credentials"),
        ):
            with self.assertRaises(HTTPException) as raised:
                Auth_endpoint.login(self.request())

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "Invalid email or password.")

    def test_login_rejects_auth_user_without_application_user(self):
        with patch.object(
            Auth_endpoint,
            "sign_in",
            return_value={"user_id": "user-a"},
        ), patch.object(Auth_endpoint, "get_user_by_id", return_value=None):
            with self.assertRaises(HTTPException) as raised:
                Auth_endpoint.login(self.request())

        self.assertEqual(raised.exception.status_code, 403)

    def test_login_request_rejects_invalid_email(self):
        with self.assertRaises(ValidationError):
            EndpointSignInRequest(email="not-an-email", password="password")

    def test_logout_calls_supabase_sign_out(self):
        with patch.object(
            Auth_endpoint.Supabase_client.auth,
            "sign_out",
        ) as sign_out:
            result = asyncio.run(
                Auth_endpoint.sign_out(SimpleNamespace(id="user-a"))
            )

        self.assertEqual(
            result,
            {"success": True, "message": "Logged out successfully."},
        )
        sign_out.assert_called_once_with()

    def test_logout_maps_provider_failure_to_http_500(self):
        with patch.object(
            Auth_endpoint.Supabase_client.auth,
            "sign_out",
            side_effect=RuntimeError("provider unavailable"),
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(Auth_endpoint.sign_out(SimpleNamespace(id="user-a")))

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(raised.exception.detail, "Unable to log out.")

    def test_refresh_token_returns_rotated_session_tokens(self):
        response = SimpleNamespace(
            session=SimpleNamespace(
                access_token="new-access-token",
                refresh_token="new-refresh-token",
            )
        )
        with patch.object(
            Auth_endpoint.Supabase_client.auth,
            "refresh_session",
            return_value=response,
        ) as refresh_session:
            result = asyncio.run(
                Auth_endpoint.refresh_token(
                    SimpleNamespace(refresh_token="old-refresh-token")
                )
            )

        self.assertEqual(
            result,
            {
                "success": True,
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
            },
        )
        refresh_session.assert_called_once_with(
            refresh_token="old-refresh-token"
        )

    def test_refresh_token_maps_provider_failure_to_401(self):
        with patch.object(
            Auth_endpoint.Supabase_client.auth,
            "refresh_session",
            side_effect=RuntimeError("invalid refresh token"),
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    Auth_endpoint.refresh_token(
                        SimpleNamespace(refresh_token="invalid-refresh-token")
                    )
                )

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(
            raised.exception.detail,
            "Invalid or expired refresh token.",
        )


class SignupTests(unittest.TestCase):
    def signup_request(self, **overrides):
        values = {
            "company_name": "Company A",
            "full_name": "Admin A",
            "email": "admin-a@example.com",
            "password": "test-password",
            "namespace": "company-a",
            "phone": "555-0100",
        }
        values.update(overrides)
        return SignUpRequest(**values)

    def test_signup_creates_auth_user_company_namespace_and_admin_response(self):
        auth_response = SimpleNamespace(user=SimpleNamespace(id="user-a"))

        with patch.object(
            Auth_endpoint.Supabase_client.auth,
            "sign_up",
            return_value=auth_response,
        ), patch.object(
            Auth_endpoint,
            "create_app",
            return_value={"company_id": "company-a"},
        ) as create_app, patch.object(
            Auth_endpoint,
            "create_namespace",
            return_value=True,
        ):
            result = Auth_endpoint.sign_up(self.signup_request())

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["role"], "admin")
        self.assertEqual(result["data"]["company_id"], "company-a")
        self.assertEqual(result["data"]["user_id"], "user-a")
        create_app.assert_called_once()

    def test_signup_rolls_back_company_and_auth_user_if_namespace_creation_fails(self):
        auth_response = SimpleNamespace(user=SimpleNamespace(id="user-a"))

        with patch.object(
            Auth_endpoint.Supabase_client.auth,
            "sign_up",
            return_value=auth_response,
        ), patch.object(
            Auth_endpoint,
            "create_app",
            return_value={"company_id": "company-a"},
        ), patch.object(
            Auth_endpoint,
            "create_namespace",
            return_value=False,
        ), patch.object(Auth_endpoint, "delete_company") as delete_company, patch.object(
            Auth_endpoint.Supabase_admin.auth.admin,
            "delete_user",
        ) as delete_user:
            with self.assertRaises(HTTPException) as raised:
                Auth_endpoint.sign_up(self.signup_request())

        self.assertEqual(raised.exception.status_code, 409)
        delete_company.assert_called_once_with("company-a")
        delete_user.assert_called_once_with("user-a")

    def test_signup_request_rejects_invalid_email_and_missing_fields(self):
        with self.assertRaises(ValidationError):
            self.signup_request(email="invalid")

        with self.assertRaises(ValidationError):
            SignUpRequest(
                company_name="Company A",
                full_name="Admin A",
                email="admin-a@example.com",
                password="test-password",
                namespace="company-a",
            )


class InvitationTests(unittest.TestCase):
    def invitation(self, **overrides):
        values = {
            "email": "invited@example.com",
            "company_id": "company-a",
            "role": "employee",
            "phone": "555-0101",
            "accepted_at": None,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        values.update(overrides)
        return values

    def request(self, **overrides):
        values = {"token": "invite-token", "password": "test-password", "full_name": "Invited"}
        values.update(overrides)
        return InvitedSignupRequest(**values)

    def test_invitation_validation_returns_email_role_and_company(self):
        invitation = self.invitation(expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
        query = Mock()
        query.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(
            data=[invitation]
        )

        with patch.object(
            Auth_endpoint.Supabase_admin,
            "table",
            return_value=query,
        ):
            result = asyncio.run(
                Auth_endpoint.validate_invitation("invite-token")
            )

        self.assertEqual(
            result,
            {
                "valid": True,
                "email": "invited@example.com",
                "role": "employee",
                "company_id": "company-a",
            },
        )

    def test_invitation_validation_rejects_missing_invalid_used_and_expired_tokens(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(Auth_endpoint.validate_invitation(""))
        self.assertEqual(raised.exception.status_code, 400)

        for invitation, detail in (
            (None, "Invalid invitation token"),
            (self.invitation(accepted_at="accepted"), "Invitation has already been used"),
            (
                self.invitation(
                    expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
                ),
                "Invitation has expired",
            ),
        ):
            query = Mock()
            query.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(
                data=[] if invitation is None else [invitation]
            )
            with patch.object(Auth_endpoint.Supabase_admin, "table", return_value=query):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(Auth_endpoint.validate_invitation("invite-token"))
            self.assertEqual(raised.exception.status_code, 400)
            self.assertEqual(raised.exception.detail, detail)

    def test_invited_signup_uses_invitation_identity_and_company(self):
        invitation = self.invitation()
        auth_response = SimpleNamespace(user=SimpleNamespace(id="user-invited"))

        with patch.object(Auth_endpoint, "get_invitation", return_value=invitation), patch.object(
            Auth_endpoint.Supabase_admin.auth.admin,
            "create_user",
            return_value=auth_response,
        ) as create_user, patch.object(
            Auth_endpoint,
            "create_invited_user",
            return_value=True,
        ) as create_invited_user, patch.object(
            Auth_endpoint,
            "mark_as_accepted",
            return_value=True,
        ):
            result = asyncio.run(Auth_endpoint.sign_up_invited(self.request()))

        self.assertEqual(result["email"], "invited@example.com")
        create_user.assert_called_once_with(
            {
                "email": "invited@example.com",
                "password": "test-password",
                "email_confirm": True,
            }
        )
        create_invited_user.assert_called_once_with(
            user_id="user-invited",
            company_id="company-a",
            full_name="Invited",
            email="invited@example.com",
            role="employee",
            phone="555-0101",
        )

    def test_invited_signup_rejects_invalid_used_and_expired_invitations(self):
        cases = (
            (None, "Invalid invitation."),
            (self.invitation(accepted_at="accepted"), "Invitation already used."),
            (
                self.invitation(
                    expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
                ),
                "Invitation has expired.",
            ),
        )
        for invitation, detail in cases:
            with patch.object(Auth_endpoint, "get_invitation", return_value=invitation):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(Auth_endpoint.sign_up_invited(self.request()))
            self.assertEqual(raised.exception.status_code, 400)
            self.assertEqual(raised.exception.detail, detail)

    def test_invited_signup_deletes_auth_user_when_application_user_creation_fails(self):
        invitation = self.invitation()
        auth_response = SimpleNamespace(user=SimpleNamespace(id="user-invited"))

        with patch.object(Auth_endpoint, "get_invitation", return_value=invitation), patch.object(
            Auth_endpoint.Supabase_admin.auth.admin,
            "create_user",
            return_value=auth_response,
        ), patch.object(
            Auth_endpoint,
            "create_invited_user",
            return_value=False,
        ), patch.object(
            Auth_endpoint.Supabase_admin.auth.admin,
            "delete_user",
        ) as delete_user:
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(Auth_endpoint.sign_up_invited(self.request()))

        self.assertEqual(raised.exception.status_code, 400)
        delete_user.assert_called_once_with("user-invited")


class ProtectedRouteIsolationTests(unittest.TestCase):
    def test_delete_user_checks_target_in_current_users_company(self):
        current_user = SimpleNamespace(id="admin-a")
        with patch.object(
            users_route,
            "get_user_by_id",
            return_value={"company_id": "company-a"},
        ), patch.object(
            users_route,
            "check_user_exists",
            return_value=False,
        ) as check_user_exists:
            with self.assertRaises(HTTPException) as raised:
                users_route.delete_user("user-b", current_user)

        self.assertEqual(raised.exception.status_code, 404)
        check_user_exists.assert_called_once_with("user-b", company_id="company-a")

    def test_admin_role_update_passes_admin_company_to_change_role(self):
        current_user = SimpleNamespace(id="admin-a")
        with patch.object(users_route, "check_user_exists", return_value=True), patch.object(
            users_route,
            "get_user_by_id",
            return_value={"company_id": "company-a"},
        ), patch.object(
            users_route,
            "change_role",
            return_value=True,
        ) as change_role:
            result = asyncio.run(
                users_route.update_role("user-b", "employee", current_user)
            )

        self.assertEqual(result, {"message": "User Role Updated Successfully"})
        change_role.assert_called_once_with(
            "user-b",
            company_id="company-a",
            role="employee",
        )

    def test_analysis_uses_authenticated_users_company(self):
        current_user = SimpleNamespace(id="hr-a")
        with patch.object(
            analysis_metrics_route,
            "get_user_by_id",
            return_value={"company_id": "company-a"},
        ), patch.object(
            analysis_metrics_route,
            "get_company_analytics",
            return_value={"company_id": "company-a"},
        ) as analytics:
            result = asyncio.run(
                analysis_metrics_route.get_analysis(current_user)
            )

        self.assertEqual(result, {"company_id": "company-a"})
        analytics.assert_called_once_with("company-a")

    def test_protected_route_dependencies_have_expected_role_matrix(self):
        routes = {
            route.path: route
            for router in (
                users_route.users_route,
                analysis_metrics_route.analysis_chat_route,
            )
            for route in router.routes
        }

        self.assertIn("/company/users/{user_id}/{role}", routes)
        self.assertIn("/analysis", routes)
        update_role_dependencies = (
            routes["/company/users/{user_id}/{role}"].dependant.dependencies
        )
        analysis_dependencies = routes["/analysis"].dependant.dependencies
        self.assertTrue(
            any(dep.call is user_auth.require_admin for dep in update_role_dependencies)
        )
        self.assertTrue(
            any(
                dep.call is user_auth.require_hr_admin
                for dep in analysis_dependencies
            )
        )


if __name__ == "__main__":
    unittest.main()
