# SkyJet Knowledge Assistant — Backend

A FastAPI backend implementing a RAG (Retrieval-Augmented Generation) pipeline
for answering employee questions against SkyJet's internal HR documents
(benefits, handbook, leave policy, performance reviews, recruitment manual).

**This reorganization preserves 100% of the original application's
behavior.** No business logic, algorithms, prompts, API contracts, or
dependencies were changed. See [`docs/MIGRATION_NOTES.md`](docs/MIGRATION_NOTES.md)
for the two narrow exceptions (a hardcoded secret, and one folder rename)
and why they were made.

## What it does

1. **Ingest** (`POST /upload`): a document (e.g. `.docx`) is saved, extracted
   into a Docling document object, split into chunks, embedded, and upserted
   into a Pinecone vector index.
2. **Chat** (`GET /chat`): a user question is either answered directly (if
   it's a greeting) or used to retrieve the top-5 most similar chunks from
   Pinecone, which are then sent to an external n8n webhook that generates
   the final answer.
3. **Health check** (`GET /health`).

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full data flow.

## Project layout

```
.
├── api.py                      # FastAPI app + all 3 endpoints
├── app/
│   ├── ingestion/               # Extract raw files -> Docling objects / text
│   ├── chunking/                # Docling objects -> RAG chunks
│   ├── embedding/                # Chunks -> vector embeddings
│   ├── models/                  # Shared data types (Final_Document)
│   └── vector_database/         # Pinecone client, insert, query, LLM webhook
│       └── llm_response/
├── data/                        # Sample source documents (.docx)
├── docs/                        # Architecture, API, env var, setup docs
├── requierments.txt             # pip dependencies (original filename kept)
├── Dockerfile
└── .env.example                 # Template for required environment variables
```

See [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) for a
file-by-file explanation of what moved and why.

## Setup

See [`docs/SETUP.md`](docs/SETUP.md) for full instructions, and
[`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) for required environment
variables.

Quick start:

```bash
pip install -r requierments.txt
cp .env.example .env   # fill in PINECONE_API_KEY
uvicorn api:app
```

## Important notices

- ⚠️ **Security**: read [`docs/SECURITY_NOTE.md`](docs/SECURITY_NOTE.md) —
  a live Pinecone API key was found hardcoded in the original source and
  has been removed from code (moved to an environment variable, with the
  owner's explicit approval). **Rotate that key** if it was ever committed
  to a shared repository.
- See [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) for pre-existing
  behavioral quirks/bugs that were intentionally left untouched per the
  "preserve exact behavior" requirement of this reorganization.
