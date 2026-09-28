# Migration Notes — Original → Reorganized

This document maps every file in the original project to its new
location and explains each change. The `.venv/` and `.idea/` directories
from the original upload were excluded (third-party installed packages
and IDE config — not project source).

## File-by-file mapping

| Original path | New path | Change |
|---|---|---|
| `api.py` | `api.py` | Same location. Only import statements updated to the new `app.*` package paths. All endpoint logic, routes, docstrings-turned-comments, and behavior unchanged. |
| `chunking/Parse_Documents.py` | `app/chunking/Parse_Documents.py` | Moved under `app/`. Logic unchanged; docstrings and internal comments added. Import paths updated (`ingestion.clean_text` → `app.ingestion.clean_text`, etc.). |
| `embedding/embedding_model.py` | `app/embedding/embedding_model.py` | Moved under `app/`. Logic unchanged; docstrings added. |
| `ingestion/clean_text.py` | `app/ingestion/clean_text.py` | Moved under `app/`. Logic unchanged; docstring added. |
| `ingestion/extraction_process.py` | `app/ingestion/extraction_process.py` | Moved under `app/`. Logic unchanged (including the pre-existing `extract_pdf` bug — see `KNOWN_ISSUES.md`); docstrings added; minor indentation cleanup in `extract_word` (whitespace only, not a logic change). |
| `models/DocModel.py` | `app/models/DocModel.py` | Moved under `app/`. Logic unchanged; docstrings and type hints on the dataclass fields added (type hints were already present in the original; formatting normalized). |
| `vector_database/pinecone_client.py` | `app/vector_database/pinecone_client.py` | Moved under `app/`. **One behavioral deviation, explicitly approved**: hardcoded API key replaced with `os.environ["PINECONE_API_KEY"]`. See `SECURITY_NOTE.md`. Index name `"hr"` and the `describe_index_stats()` startup call are unchanged. |
| `vector_database/insertion.py` | `app/vector_database/insertion.py` | Moved under `app/`. Logic unchanged; import path updated; docstrings added. |
| `vector_database/query.py` | `app/vector_database/query.py` | Moved under `app/`. Logic unchanged; import paths updated (including the `LLM_Response` → `llm_response` rename, see below); docstrings added. |
| `vector_database/LLM_Response/LLM.py` | `app/vector_database/llm_response/LLM.py` | Moved under `app/`, **parent folder renamed** `LLM_Response` → `llm_response` (see below). Logic, webhook URLs, and the `__main__` block unchanged; docstrings added. |
| `data/*.docx` | `data/*.docx` | Unchanged, copied as-is. |
| `requierments.txt` | `requierments.txt` | Unchanged (filename typo kept intentionally — see `KNOWN_ISSUES.md` #7). |
| `Dockerfile` | `Dockerfile` | Unchanged byte-for-byte (including the `WORKDIR / app` typo — see `KNOWN_ISSUES.md` #6). |
| *(none)* | `.env.example` | **New file.** Documents the `PINECONE_API_KEY` variable required after the security fix. |
| *(none)* | `app/__init__.py` and one `__init__.py` per sub-package | **New files.** The original project had no `__init__.py` files anywhere; Python 3's implicit namespace packages made the flat imports (`from chunking.Parse_Documents import ...` etc.) work anyway. Adding explicit `__init__.py` files with module-level docstrings is additive only — it does not change import resolution for any of the import statements used in this project, and was verified by re-running the full import graph (see validation section of the handoff summary). |
| *(none)* | `docs/*.md` | **New files.** All documentation described in this migration guide. |

## Why the top-level `app/` package was introduced

The original project used five top-level packages directly on the Python
path (`chunking`, `embedding`, `ingestion`, `models`, `vector_database`).
Nesting them under a single `app/` package:

- Makes the project root cleaner (only `api.py`, `app/`, `data/`,
  `docs/`, config files at top level).
- Avoids potential top-level name collisions with third-party packages
  of the same name (e.g. `models` is a common name).
- Is a widely recognized convention for FastAPI projects.

Every internal module's **name and relative position to its siblings**
is unchanged — only the common `app.` prefix was added. This is a
mechanical, verifiable transformation: every `from X.Y import Z` in the
original became `from app.X.Y import Z` (or, for the one renamed folder,
`from app.vector_database.llm_response.LLM import ...`).

## The one folder rename: `LLM_Response` → `llm_response`

This is the only file/folder **name** change in the whole project. It
was made because:

- It was the only mixed-case package name in an otherwise all-lowercase
  package naming scheme (`chunking`, `embedding`, `ingestion`, `models`,
  `vector_database`), which is inconsistent with PEP 8 package naming
  conventions.
- All three internal import sites (`api.py`, `vector_database/query.py`,
  and the folder's own contents) were updated consistently, and the
  full import graph was re-verified after the rename (see validation
  notes).

If you'd prefer to keep the original `LLM_Response` casing, this is a
trivial one-line change in three files — let me know and I'll revert
just this rename.

## What was explicitly NOT changed

- No business logic, algorithm, or computation was altered anywhere.
- No prompts (webhook payload shapes) were altered.
- No API endpoint paths, methods, query/body parameters, or response
  shapes were altered.
- No dependency versions in `requierments.txt` were altered.
- No function/class/variable names were altered (except the one folder
  rename above, which only affects the import path, not any symbol
  name).
- The pre-existing bugs and quirks listed in `KNOWN_ISSUES.md` are all
  preserved exactly.
