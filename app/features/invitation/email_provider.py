from __future__ import annotations

import os
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

import resend


INVITATION_BASE_URL = (
    "https://numeric-oven-suitcase.ngrok-free.dev/company/invite/validate"
)


@dataclass(frozen=True)
class CapturedInvitationEmail:
    recipient_email: str
    subject: str
    invitation_url: str


class EmailProvider(Protocol):
    def send_invitation(
        self,
        recipient_email: str,
        company_name: str,
        role: str,
        invitation_token: str,
    ) -> None:
        ...


class ResendEmailProvider:
    def send_invitation(
        self,
        recipient_email: str,
        company_name: str,
        role: str,
        invitation_token: str,
    ) -> None:
        sender = os.getenv("RESEND_FROM_EMAIL")
        if not sender:
            raise RuntimeError(
                "RESEND_FROM_EMAIL must be configured with an address "
                "from a verified production Resend domain."
            )

        resend.Emails.send(
            {
                "from": sender,
                "to": recipient_email,
                "subject": f"Invitation to {company_name}",
                "html": f"""
                    <h2>You're invited!</h2>

                    <p>You have been invited to join
                    <strong>{company_name}</strong>.</p>

                    <p>Role: <strong>{role}</strong></p>

                    <p>Your invitation url:</p>

                    <a href="{INVITATION_BASE_URL}?token={invitation_token}">
                        Accept Invitation
                    </a>
                """,
            }
        )


class TestEmailProvider:
    """Captures test email metadata without sending or logging tokens."""

    def __init__(self) -> None:
        self._messages: list[CapturedInvitationEmail] = []
        self._lock = Lock()

    def send_invitation(
        self,
        recipient_email: str,
        company_name: str,
        role: str,
        invitation_token: str,
    ) -> None:
        message = CapturedInvitationEmail(
            recipient_email=recipient_email,
            subject=f"Invitation to {company_name}",
            invitation_url=f"{INVITATION_BASE_URL}?token={invitation_token}",
        )
        with self._lock:
            self._messages.append(message)

    def latest(self) -> CapturedInvitationEmail | None:
        with self._lock:
            return self._messages[-1] if self._messages else None

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()


def _test_environment_enabled() -> bool:
    return os.getenv("TEST_ENV", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_email_provider() -> EmailProvider:
    if not _test_environment_enabled():
        return ResendEmailProvider()

    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        raise RuntimeError(
            "TEST_ENV is enabled but RUN_INTEGRATION_TESTS=1 is missing; "
            "refusing to select the test email provider."
        )

    return test_email_provider


test_email_provider = TestEmailProvider()
