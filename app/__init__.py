"""
SkyJet Knowledge Assistant — application package.

This package contains the full backend implementation for the RAG
(Retrieval-Augmented Generation) pipeline: document ingestion, chunking,
embedding, vector storage/retrieval (Pinecone), and LLM response
generation (via an external n8n webhook).

Sub-packages:
    - chunking:        Splits parsed documents into RAG-ready chunks.
    - embedding:        Converts text chunks into vector embeddings.
    - ingestion:        Extracts and cleans raw document content.
    - models:           Shared data structures (e.g. Final_Document).
    - vector_database:  Pinecone client, insertion, query, and LLM response.

See docs/ARCHITECTURE.md for the full data flow diagram and docs/README.md
for setup instructions.
"""

