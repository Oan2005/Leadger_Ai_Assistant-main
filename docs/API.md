# API Reference

Base app: `api.py` (`FastAPI()` instance named `app`). Run with
`uvicorn api:app`.

---

## `GET /chat`

Answer a user's question using retrieval-augmented generation, or a direct
greeting response.

**Query parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `user_question` | string | yes | The question or greeting text. |

**Behavior**

- If `user_question` (lowercased, stripped) matches a known greeting
  (`"hi"`, `"hello"`, `"how are you"`, etc. — see
  `app.vector_database.query.is_greeting` for the full list), the request
  is routed to `LLM_response_greeting`, which POSTs directly to the
  greeting n8n webhook.
- Otherwise, the top **5** most similar chunks are retrieved from Pinecone
  (`pinecone_query(user_question, top_k=5)`), bundled with the question
  into `{"user_question": ..., "documents": [...]}`, and POSTed to the
  main n8n webhook via `LLM_response`.

**Response**

```json
{ "message": "<answer text, or error dict, or error string>" }
```

Any exception raised during processing is caught and returned as
`{"message": str(e)}` (HTTP 200 is still returned — errors are not
surfaced via HTTP status codes).

---

## `GET /health`

Basic health check.

**Response**

```json
{ "status": "healthy" }
```

---

## `POST /upload`

Ingest a document into the knowledge base.

**Body**: `multipart/form-data` with a single `file` field.

**Behavior**

1. Reads the uploaded file's bytes and writes them to disk in the current
   working directory, using the **original uploaded filename**
   (no sanitization or uniqueness check — see `docs/KNOWN_ISSUES.md`).
2. Extracts the file into a Docling document object
   (`extract_to_objects`).
3. Chunks the document for RAG (`Parse_Doc_for_Rag`), tagging each chunk
   with heading hierarchy and table membership.
4. Embeds every chunk (`embedd_chunks`) using `BAAI/bge-base-en-v1.5`.
5. Upserts all embedded chunks **except the first** (`embedd_docs[1:]`,
   dropping the placeholder — see `docs/KNOWN_ISSUES.md`) into the
   Pinecone index `"hr"`, namespace `"__default__"`.

**Response**

```json
{ "status": "Success" }
```

On any exception: `{"message": str(e)}`.
