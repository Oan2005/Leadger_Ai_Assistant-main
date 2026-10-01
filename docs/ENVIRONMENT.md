# Environment Variables

Copy `.env.example` to `.env` and fill in real values, or export these
variables in your shell/deployment environment before running the app.

| Variable | Required | Description |
|---|---|---|
| `PINECONE_API_KEY` | **Yes** | API key for the Pinecone project hosting the `"hr"` index. Read by `app/vector_database/pinecone_client.py`. **This did not exist in the original project** — the key was previously hardcoded in source. See `docs/SECURITY_NOTE.md`. |
| `RESEND_API_KEY` | **Yes for production email** | Resend API key used to send invitation emails. |
| `RESEND_FROM_EMAIL` | **Yes for production email** | Sender address on a domain verified in Resend, for example `invitations@mail.example.com`. The testing-only `onboarding@resend.dev` address must not be used in production. |
| `MAX_UPLOAD_SIZE_MB` | No | Maximum document upload size in megabytes. Defaults to `25`. Uploads over this limit receive `413`. |

## Not environment-configurable (unchanged from original)

The following values remain hardcoded in source, exactly as in the
original project, since changing them was out of scope for this
reorganization:

- Pinecone index name: `"hr"` (`pinecone_client.py`)
- Pinecone namespace: `"__default__"` (`insertion.py`)
- n8n webhook URLs (`app/vector_database/llm_response/LLM.py`):
  - `webhook_url` — main chat webhook
  - `webhook_greeting_url` — greeting webhook
- Embedding model name: `"BAAI/bge-base-en-v1.5"` (`embedding_model.py`)
- Chunking tokenizer/limits: `"sentence-transformers/all-MiniLM-L6-v2"`,
  `max_tokens=256` (`Parse_Documents.py`)

If you want these configurable via environment variables too, that would
be a behavior-preserving follow-up change, but it was not requested and
was not made here.
