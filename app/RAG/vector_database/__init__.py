"""
vector_database
================

Everything related to the Pinecone vector store: client
initialization, chunk insertion (upsert), similarity query, and
LLM-based answer generation.

Modules:
    - pinecone_client: Initializes the shared Pinecone client/index.
    - insertion:       `insert_chunks` — upserts embedded chunks.
    - query:           `pinecone_query`, `is_greeting` — retrieval and
                        simple greeting detection.
    - llm_response:     (see llm_response/__init__.py) LLM answer
                         generation via an external n8n webhook.
"""


