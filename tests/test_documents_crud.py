import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

from app.database.crud import documents_crud


DOCUMENT_COLUMNS = {
    "document_id",
    "company_id",
    "uploaded_by",
    "filename",
    "version",
    "status",
    "pinecone_namespace",
    "total_chunks",
    "uploaded_at",
    "updated_at",
    "deleted_at",
}


def document_record(document_id, company_id, status="ready"):
    now = datetime.now(timezone.utc)
    return {
        "document_id": document_id,
        "company_id": company_id,
        "uploaded_by": "user-1",
        "filename": f"{document_id}.pdf",
        "version": 1,
        "status": status,
        "pinecone_namespace": f"namespace-{document_id}",
        "total_chunks": 3,
        "uploaded_at": now,
        "updated_at": now,
        "deleted_at": None if status != "deleted" else now,
    }


class FakeCursor:
    def __init__(self, *, records=None, record=None, rowcount=None, error=None):
        self.records = records or []
        self.record = record
        self.rowcount = len(self.records) if rowcount is None else rowcount
        self.error = error
        self.executed = None
        self.cursor_factory = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params):
        self.executed = (query, params)
        if self.error:
            raise self.error

    def fetchall(self):
        return self.records

    def fetchone(self):
        return self.record


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self, cursor_factory=None):
        self.cursor_instance.cursor_factory = cursor_factory
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class DocumentsCrudTests(unittest.TestCase):
    def test_get_documents_returns_all_active_records_with_expected_columns(self):
        records = [
            document_record("document-1", "company-a"),
            document_record("document-2", "company-a", status="archived"),
        ]
        cursor = FakeCursor(records=records)
        connection = FakeConnection(cursor)

        with patch.object(documents_crud, "connect_to_database", return_value=connection):
            result = documents_crud.get_documents("company-a")

        self.assertEqual(result, {"records": records})
        self.assertEqual(len(result["records"]), 2)
        for record in result["records"]:
            self.assertIsInstance(record, dict)
            self.assertEqual(set(record), DOCUMENT_COLUMNS)
        self.assertIs(cursor.cursor_factory, RealDictCursor)
        query, params = cursor.executed
        self.assertIn("company_id = %s", query)
        self.assertIn("status != 'deleted'", query)
        self.assertEqual(params, ("company-a",))

    def test_get_documents_returns_false_when_company_has_no_documents(self):
        cursor = FakeCursor(records=[])
        connection = FakeConnection(cursor)

        with patch.object(documents_crud, "connect_to_database", return_value=connection):
            result = documents_crud.get_documents("company-without-documents")

        self.assertFalse(result)

    def test_get_documents_returns_false_when_all_company_documents_are_deleted(self):
        cursor = FakeCursor(records=[])
        connection = FakeConnection(cursor)

        with patch.object(documents_crud, "connect_to_database", return_value=connection):
            result = documents_crud.get_documents("company-with-deleted-documents")

        self.assertFalse(result)
        query, params = cursor.executed
        self.assertIn("status != 'deleted'", query)
        self.assertEqual(params, ("company-with-deleted-documents",))

    def test_get_documents_passes_company_id_and_preserves_company_isolation(self):
        records = [document_record("document-a", "company-a")]
        cursor = FakeCursor(records=records)
        connection = FakeConnection(cursor)

        with patch.object(documents_crud, "connect_to_database", return_value=connection):
            result = documents_crud.get_documents("company-a")

        self.assertEqual(
            {record["company_id"] for record in result["records"]},
            {"company-a"},
        )
        self.assertNotIn("company-b", {record["company_id"] for record in result["records"]})
        self.assertEqual(cursor.executed[1], ("company-a",))

    def test_get_documents_maps_database_errors_to_http_500(self):
        cursor = FakeCursor(error=RuntimeError("database unavailable"))
        connection = FakeConnection(cursor)

        with patch.object(documents_crud, "connect_to_database", return_value=connection):
            with self.assertRaises(HTTPException) as raised:
                documents_crud.get_documents("company-a")

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(raised.exception.detail, "Unable to retrieve documents.")

    def test_create_documents_inserts_record_and_commits(self):
        record = document_record("document-1", "company-a")
        cursor = FakeCursor(record=record)
        connection = FakeConnection(cursor)
        data = documents_crud.documents(
            document_id="document-1",
            company_id="company-a",
            uploaded_by="user-1",
            filename="document-1.pdf",
            version=1,
            status="ready",
            pinecone_namespace="namespace-document-1",
            total_chunks=3,
        )

        with patch.object(documents_crud, "connect_to_database", return_value=connection):
            result = documents_crud.create_documents(data)

        self.assertEqual(result, {"success": True, "message": record})
        self.assertEqual(connection.commits, 1)
        query, params = cursor.executed
        self.assertIn("INSERT INTO documents", query)
        self.assertEqual(params[0:2], ("document-1", "company-a"))

    def test_delete_documents_updates_only_matching_company_and_commits(self):
        cursor = FakeCursor(rowcount=1)
        connection = FakeConnection(cursor)

        with patch.object(documents_crud, "connect_to_database", return_value=connection):
            result = documents_crud.delete_documents_from_database(
                "document-1",
                "company-a",
            )

        self.assertTrue(result["success"])
        self.assertEqual(connection.commits, 1)
        query, params = cursor.executed
        self.assertIn("status = 'deleted'", query)
        self.assertIn("document_id = %s AND company_id = %s", query)
        self.assertEqual(params, ("document-1", "company-a"))

    def test_delete_documents_returns_false_when_no_row_matches(self):
        cursor = FakeCursor(rowcount=0)
        connection = FakeConnection(cursor)

        with patch.object(documents_crud, "connect_to_database", return_value=connection):
            result = documents_crud.delete_documents_from_database(
                "missing-document",
                "company-a",
            )

        self.assertFalse(result)
        self.assertEqual(connection.commits, 0)

    def test_delete_documents_maps_database_errors_to_http_500(self):
        cursor = FakeCursor(error=RuntimeError("database unavailable"))
        connection = FakeConnection(cursor)

        with patch.object(documents_crud, "connect_to_database", return_value=connection):
            with self.assertRaises(HTTPException) as raised:
                documents_crud.delete_documents_from_database(
                    "document-1",
                    "company-a",
                )

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(
            raised.exception.detail,
            "Unable to update document status.",
        )
        self.assertEqual(connection.rollbacks, 1)

    def test_archive_and_unarchive_documents_return_expected_results(self):
        archive_cursor = FakeCursor(record=("document-1",))
        archive_connection = FakeConnection(archive_cursor)
        with patch.object(
            documents_crud,
            "connect_to_database",
            return_value=archive_connection,
        ):
            archived = documents_crud.archive_documents_from_database(
                "document-1",
                "company-a",
            )

        self.assertTrue(archived["success"])
        self.assertEqual(archive_connection.commits, 1)

        unarchive_cursor = FakeCursor(rowcount=1)
        unarchive_connection = FakeConnection(unarchive_cursor)
        with patch.object(
            documents_crud,
            "connect_to_database",
            return_value=unarchive_connection,
        ):
            unarchived = documents_crud.unrchive_documents_from_database(
                "document-1",
                "company-a",
            )

        self.assertEqual(unarchived, {"success": True})
        self.assertEqual(unarchive_connection.commits, 1)


if __name__ == "__main__":
    unittest.main()
