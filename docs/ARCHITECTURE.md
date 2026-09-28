# Architecture

## Overview

This backend is a simple, mostly-linear RAG pipeline exposed through three
FastAPI endpoints. There is no database beyond Pinecone (the vector store);
the "LLM" itself is not called in-process — it's delegated to an external
n8n workflow via webhook.

## Data flow

### 1. Ingestion (`POST /upload`)

```
UploadFile
   │
   ▼
api.upload_file_into_db
   │  saves file to disk (cwd, using original filename)
   ▼
app.ingestion.extraction_process.extract_to_objects(file_path)
   │  Docling DocumentConverter -> DoclingDocument
   ▼
app.chunking.Parse_Documents.Parse_Doc_for_Rag(doc, file_path)
   │  HybridChunker splits into chunks
   │  app.ingestion.clean_text.clean_text() cleans each chunk's text
   │  -> list[Final_Document] (values=[] still empty)
   ▼
app.embedding.embedding_model.embedd_chunks(chunks)
   │  SentenceTransformer("BAAI/bge-base-en-v1.5").encode(...)
   │  -> list[dict] Pinecone-ready records
   │     NOTE: index 0 is always an empty {} placeholder (see
   │     docs/KNOWN_ISSUES.md) — callers slice with [1:]
   ▼
app.vector_database.insertion.insert_chunks(records[1:])
   │  index.upsert(vectors=records, namespace="__default__")
   ▼
Pinecone index "hr"
```

### 2. Chat (`GET /chat?user_question=...`)

```
user_question
   │
   ▼
app.vector_database.query.is_greeting(user_question)
   │
   ├── True ──► app.vector_database.llm_response.LLM.LLM_response_greeting
   │              │  POST to n8n greeting webhook
   │              ▼
   │            {"message": <answer or error dict>}
   │
   └── False ─► app.vector_database.query.pinecone_query(user_question, top_k=5)
                  │  embeds question with the SAME embedding_model instance
                  │  used at ingestion time (imported directly, not reloaded)
                  │  index.query(...) -> top-5 matches with metadata.text
                  ▼
                {"user_question": ..., "documents": [...]}
                  │
                  ▼
                app.vector_database.llm_response.LLM.LLM_response(payload)
                  │  POST to n8n main webhook
                  ▼
                {"message": <answer text>}
```

### 3. Health (`GET /health`)

Static `{"status": "healthy"}` response — no dependencies touched.

## External dependencies

| Dependency | Role | Where |
|---|---|---|
| Docling | Document parsing + chunking (`HybridChunker`) | `app.ingestion`, `app.chunking` |
| sentence-transformers | Embedding model (`BAAI/bge-base-en-v1.5`) | `app.embedding` |
| Pinecone | Vector storage + similarity search, index name `"hr"` | `app.vector_database` |
| n8n (external webhooks) | Actual LLM call / answer generation | `app.vector_database.llm_response` |

## Module dependency graph

```
api.py
 ├─ app.chunking.Parse_Documents
 │    ├─ app.ingestion.clean_text
 │    └─ app.models.DocModel
 ├─ app.embedding.embedding_model
 ├─ app.ingestion.extraction_process
 ├─ app.vector_database.llm_response.LLM
 ├─ app.vector_database.insertion
 │    └─ app.vector_database.pinecone_client
 └─ app.vector_database.query
      ├─ app.embedding.embedding_model
      ├─ app.vector_database.llm_response.LLM
      └─ app.vector_database.pinecone_client
```

No circular imports exist in the original or the reorganized project.
