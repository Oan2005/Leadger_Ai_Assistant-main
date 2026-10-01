import unittest
from datetime import datetime, timezone
import asyncio
import tempfile
from unittest.mock import patch

from app.database.crud import analysis_crud, documents_crud, invitation_crud
from app.database.crud import users_crud
from app.services import upload_limits
from app.models.pydantic_classes.auth_pydantic import (
    InvitedSignupRequest,
    SignUpInvitationRequest,
)
from pydantic import ValidationError


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.rowcount = 1 if row else 0
        self.executed = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params):
        self.executed = (query, params)

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row):
        self.cursor_instance = FakeCursor(row)
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1


class ApiFixTests(unittest.TestCase):
    def test_upload_size_limit_rejects_oversized_stream(self):
        class Upload:
            def __init__(self):
                self.chunks = [b"12345", b"67890", b""]

            async def read(self, _):
                return self.chunks.pop(0)

        with tempfile.TemporaryDirectory() as directory:
            destination = f"{directory}\\upload.bin"
            with patch.object(upload_limits, "MAX_UPLOAD_SIZE_BYTES", 9):
                with self.assertRaises(Exception) as error:
                    asyncio.run(
                        upload_limits.save_upload_with_limit(
                            Upload(),
                            destination,
                        )
                    )

        self.assertEqual(error.exception.status_code, 413)

    def test_mark_as_accepted_commits_and_requires_unused_unexpired_invitation(self):
        accepted_at = datetime.now(timezone.utc)
        row = (
            "invitation-id", "person@example.com", "company-a", "employee",
            "hash", "admin-id", "555", accepted_at, accepted_at,
            accepted_at,
        )
        connection = FakeConnection(row)

        with patch.object(
            invitation_crud,
            "connect_to_database",
            return_value=connection,
        ):
            result = invitation_crud.mark_as_accepted("hash")

        self.assertEqual(result["company_id"], "company-a")
        self.assertEqual(connection.commits, 1)
        query, _ = connection.cursor_instance.executed
        self.assertIn("accepted_at IS NULL", query)
        self.assertIn("expires_at > NOW()", query)

    def test_empty_response_time_average_is_safe(self):
        cursor = FakeCursor((None,))
        connection = FakeConnection((None,))
        connection.cursor_instance = cursor

        with patch.object(
            analysis_crud,
            "connect_to_database",
            return_value=connection,
        ):
            result = analysis_crud.get_avg_response_time("company-a")

        self.assertIsNone(result)

    def test_missing_document_record_is_not_reported_as_archive_success(self):
        connection = FakeConnection(None)

        with patch.object(
            documents_crud,
            "connect_to_database",
            return_value=connection,
        ):
            result = documents_crud.archive_documents_from_database(
                "document-id",
                "company-a",
            )

        self.assertFalse(result)

    def test_missing_document_record_is_not_reported_as_unarchive_success(self):
        connection = FakeConnection(None)

        with patch.object(
            documents_crud,
            "connect_to_database",
            return_value=connection,
        ):
            result = documents_crud.unrchive_documents_from_database(
                "document-id",
                "company-a",
            )

        self.assertFalse(result["success"])

    def test_invitation_role_and_password_validation(self):
        with self.assertRaises(ValidationError):
            SignUpInvitationRequest(
                email="person@example.com",
                role="owner",
                phone="555",
            )

        with self.assertRaises(ValidationError):
            InvitedSignupRequest(
                token="",
                password="short",
                full_name="Person",
            )

    def test_user_delete_rejects_a_different_company(self):
        with patch.object(
            users_crud,
            "get_user_by_id",
            return_value={"company_id": "company-b", "email": "person@example.com"},
        ), patch.object(
            users_crud.Supabase_admin.auth.admin,
            "delete_user",
        ) as delete_user:
            result = users_crud.delete_user_by_id("user-b", "company-a")

        self.assertFalse(result["success"])
        delete_user.assert_not_called()


if __name__ == "__main__":
    unittest.main()
