from __future__ import annotations

from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import pytest

from app.features.invitation import routes
from app.features.invitation.email_provider import ResendEmailProvider


def test_invitation_email_is_captured_without_resend(
    captured_invitation_email,
    monkeypatch,
):
    monkeypatch.setattr(routes, "resend", None)

    routes.send_invitation_email(
        recipient_email="test-user-company-a@example.test",
        company_name="supplycmd",
        role="employee",
        invitation_token="opaque-test-token",
    )

    message = captured_invitation_email.latest()
    assert message is not None
    assert message.recipient_email == "test-user-company-a@example.test"
    assert message.subject == "Invitation to supplycmd"
    parsed = urlparse(message.invitation_url)
    assert parse_qs(parsed.query)["token"] == ["opaque-test-token"]


def test_test_provider_requires_explicit_integration_opt_in(monkeypatch):
    monkeypatch.setenv("TEST_ENV", "true")
    monkeypatch.delenv("RUN_INTEGRATION_TESTS", raising=False)

    from app.features.invitation.email_provider import get_email_provider

    with pytest.raises(RuntimeError, match="RUN_INTEGRATION_TESTS"):
        get_email_provider()


def test_production_mode_selects_resend_provider(monkeypatch):
    monkeypatch.delenv("TEST_ENV", raising=False)
    monkeypatch.delenv("RUN_INTEGRATION_TESTS", raising=False)

    from app.features.invitation.email_provider import get_email_provider

    assert isinstance(get_email_provider(), ResendEmailProvider)


def test_resend_uses_configured_sender_and_dynamic_recipient(monkeypatch):
    monkeypatch.setenv("RESEND_FROM_EMAIL", "invitations@mail.example.com")
    provider = ResendEmailProvider()
    with patch("app.features.invitation.email_provider.resend.Emails.send") as send:
        provider.send_invitation(
            recipient_email="arbitrary-recipient@example.test",
            company_name="supplycmd",
            role="employee",
            invitation_token="opaque-test-token",
        )

    payload = send.call_args.args[0]
    assert payload["from"] == "invitations@mail.example.com"
    assert payload["to"] == "arbitrary-recipient@example.test"


def test_resend_requires_a_configured_sender(monkeypatch):
    monkeypatch.delenv("RESEND_FROM_EMAIL", raising=False)

    with pytest.raises(RuntimeError, match="RESEND_FROM_EMAIL"):
        ResendEmailProvider().send_invitation(
            recipient_email="arbitrary-recipient@example.test",
            company_name="supplycmd",
            role="employee",
            invitation_token="opaque-test-token",
        )
