# Project Structure

```
.
├── api.py                                # FastAPI app: /chat, /health, /upload
├── app/
│   ├── __init__.py                       # Package overview docstring
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── extraction_process.py         # Docling extraction (+ legacy PDF/TXT/DOCX helpers, unused)
│   │   └── clean_text.py                 # Per-chunk text cleanup
│   ├── chunking/
│   │   ├── __init__.py
│   │   └── Parse_Documents.py            # Docling object -> list[Final_Document]
│   ├── embedding/
│   │   ├── __init__.py
│   │   └── embedding_model.py            # Loads BAAI/bge-base-en-v1.5, embeds chunks
│   ├── models/
│   │   ├── __init__.py
│   │   └── DocModel.py                   # Final_Document dataclass
│   └── vector_database/
│       ├── __init__.py
│       ├── pinecone_client.py            # Shared Pinecone client + "hr" index
│       ├── insertion.py                  # Upsert embedded chunks
│       ├── query.py                      # Similarity search + greeting detection
│       └── llm_response/
│           ├── __init__.py
│           └── LLM.py                    # n8n webhook calls -> final answer text
├── data/
│   └── *.docx                            # Sample SkyJet HR documents
├── docs/
│   ├── ARCHITECTURE.md                   # Data flow, dependency graph
│   ├── API.md                            # Endpoint reference
│   ├── ENVIRONMENT.md                    # Required env vars
│   ├── SETUP.md                          # Install/run instructions
│   ├── SECURITY_NOTE.md                  # API key remediation details
│   ├── KNOWN_ISSUES.md                   # Pre-existing bugs, left untouched
│   ├── MIGRATION_NOTES.md                # Full old-path -> new-path mapping
│   └── PROJECT_STRUCTURE.md              # This file
├── requierments.txt                      # pip dependencies (original filename)
├── Dockerfile
├── .env.example                          # Template for PINECONE_API_KEY
└── README.md
```

## Folder-by-folder purpose

### `app/ingestion/`
Turns a raw uploaded file into structured content. `extract_to_objects`
(Docling-based) is the one actually used by `/upload`; `extract_pdf`,
`extract_txt`, and `extract_word` are legacy per-format helpers not
currently wired into the pipeline, but were preserved exactly as they
were (unused code is not "dead code to remove" under this task's rules —
only structural reorganization was in scope). `clean_text` does small
per-chunk text cleanup used later during chunking.

### `app/chunking/`
Owns the document → RAG-chunk transformation. `Parse_Doc_for_Rag` is the
single public entry point, used by `/upload` right after extraction.

### `app/embedding/`
Owns the embedding model lifecycle. The model is loaded once at import
time (module-level `embedding_model` variable) and reused by both the
ingestion path (`embedd_chunks`) and the query path
(`app.vector_database.query` imports `embedding_model` directly) — this
sharing is intentional in the original code and preserved.

### `app/models/`
Currently holds a single shared type, `Final_Document`, used as the
common "chunk record" shape from chunking through to embedding.

### `app/vector_database/`
Everything Pinecone- and LLM-webhook-related:
- `pinecone_client.py` is the single source of the shared `index` object,
  imported by both `insertion.py` and `query.py`.
- `insertion.py` and `query.py` are the write and read sides of the
  vector store, respectively.
- `llm_response/LLM.py` is a distinct concern (calling out to n8n for
  the actual generated answer) and was already separated into its own
  sub-folder in the original project — that separation was kept, only
  the folder's casing was normalized (see `MIGRATION_NOTES.md`).

### `data/`
Sample source documents used for testing ingestion. Not read by any code
path automatically — documents are ingested via the `/upload` endpoint.

### `docs/`
All documentation produced by this reorganization pass.
