from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from main import app
from app.routes import employee_assistant_route as route


@pytest.fixture
def chat_client(monkeypatch):
    class User:
        id = "test-user-id"

    app.dependency_overrides[route.get_current_user] = lambda: User()
    monkeypatch.setattr(
        route,
        "get_user_by_id",
        lambda user_id: {
            "user_id": user_id,
            "company_id": "test-company-id",
        },
    )
    monkeypatch.setattr(
        route,
        "get_namespace_by_company_id",
        lambda company_id: {
            "success": True,
            "namespace": "test-namespace",
        },
    )

    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _successful_llm_response():
    return {
        "response": '{"answer": "Test answer", "confidence": 0.9}',
        "usage": SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    }


def _configure_successful_pipeline(monkeypatch, conversation_id="conversation-id"):
    calls = {
        "retrieval": 0,
        "llm": 0,
        "conversation": 0,
        "documents": 0,
        "analysis": 0,
    }

    def retrieve(**kwargs):
        calls["retrieval"] += 1
        return [
            {
                "text": "Test policy",
                "retrieval_score": 0.9,
                "document_id": "document-id",
                "chunk_index": 0,
            }
        ]

    def llm(**kwargs):
        calls["llm"] += 1
        return _successful_llm_response()

    def create(**kwargs):
        calls["conversation"] += 1
        return {"success": True, "conversation_id": conversation_id}

    def save_documents(**kwargs):
        calls["documents"] += 1

    def analyze(**kwargs):
        calls["analysis"] += 1
        return {"status": True, "message": {}}

    monkeypatch.setattr(route, "pinecone_query", retrieve)
    monkeypatch.setattr(route, "LLM_response", llm)
    monkeypatch.setattr(route, "create_conversation", create)
    monkeypatch.setattr(route, "create_documents_from_pinecone", save_documents)
    monkeypatch.setattr(route, "analysis_process", analyze)
    return calls


@pytest.mark.parametrize("question", ["", "   ", "\t\n"])
def test_empty_question_is_rejected_before_pipeline(
    chat_client, monkeypatch, question
):
    calls = _configure_successful_pipeline(monkeypatch)

    response = chat_client.post(
        "/employee/question",
        params={"question": question},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question must not be empty."
    assert calls == {
        "retrieval": 0,
        "llm": 0,
        "conversation": 0,
        "documents": 0,
        "analysis": 0,
    }


def test_analysis_failure_is_not_reported_as_success(chat_client, monkeypatch):
    calls = _configure_successful_pipeline(monkeypatch)
    monkeypatch.setattr(
        route,
        "analysis_process",
        lambda **kwargs: {"status": False, "message": "failure"},
    )

    response = chat_client.post(
        "/employee/question",
        params={"question": "What is the leave policy?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Unable to complete conversation analysis."
    assert calls["conversation"] == 1
    assert calls["documents"] == 1


def test_conversation_failure_does_not_start_analysis(chat_client, monkeypatch):
    calls = _configure_successful_pipeline(monkeypatch)
    monkeypatch.setattr(
        route,
        "create_conversation",
        lambda **kwargs: {"success": False, "error": "database unavailable"},
    )

    response = chat_client.post(
        "/employee/question",
        params={"question": "What is the leave policy?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Unable to save the conversation."
    assert calls["documents"] == 0
    assert calls["analysis"] == 0


def test_retrieval_failure_does_not_call_downstream_stages(
    chat_client, monkeypatch
):
    calls = _configure_successful_pipeline(monkeypatch)
    monkeypatch.setattr(
        route,
        "pinecone_query",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("retrieval unavailable")
        ),
    )

    response = chat_client.post(
        "/employee/question",
        params={"question": "What is the leave policy?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The document retrieval service is unavailable."
    )
    assert calls["llm"] == 0
    assert calls["conversation"] == 0
    assert calls["analysis"] == 0


def test_llm_failure_does_not_create_persistence_records(
    chat_client, monkeypatch
):
    calls = _configure_successful_pipeline(monkeypatch)
    monkeypatch.setattr(
        route,
        "LLM_response",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("provider unavailable")
        ),
    )

    response = chat_client.post(
        "/employee/question",
        params={"question": "What is the leave policy?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "The answer service is unavailable."
    assert calls["conversation"] == 0
    assert calls["analysis"] == 0


def test_successful_chat_runs_all_stages(chat_client, monkeypatch):
    calls = _configure_successful_pipeline(monkeypatch)

    response = chat_client.post(
        "/employee/question",
        params={"question": "What is the leave policy?"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Test answer"
    assert response.json()["confidence"] == 0.9
    assert calls == {
        "retrieval": 1,
        "llm": 1,
        "conversation": 1,
        "documents": 1,
        "analysis": 1,
    }
