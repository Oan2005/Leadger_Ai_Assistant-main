"""
embedding_model
================

Loads the `BAAI/bge-base-en-v1.5` sentence-transformer model once at
import time and uses it to embed chunk text for storage in Pinecone.

Note: The same `embedding_model` instance is imported directly by
`app.vector_database.query` to embed user questions at query time,
ensuring embedding space consistency between ingestion and retrieval.

Dependencies:
    - sentence_transformers.SentenceTransformer

Input:
    - chunks: list of `Final_Document`-like objects with `.id` and
      `.metadata["text"]`.

Output:
    - list[dict]: Pinecone-ready vector records with `id`, `values`,
      and `metadata`. NOTE: the first element of the returned list is
      always an empty `{}` placeholder (existing behavior — callers
      such as `main.py` slice it off with `embedd_docs[1:]`).
"""

from sentence_transformers import SentenceTransformer
from transformers import logging
logging.set_verbosity_error()
encoder_model = SentenceTransformer("BAAI/bge-base-en-v1.5")


def embedd_chunks(chunks: list):
    """
    Embed a list of document chunks into Pinecone-ready vector records.

    Args:
        chunks (list): Chunk objects (e.g. `Final_Document`) each
            exposing `.id` and `.metadata["text"]`.

    Returns:
        list[dict]: A list beginning with an empty placeholder dict,
        followed by one `{"id", "values", "metadata"}` record per input
        chunk. (Existing behavior — see note above.)
    """
    rag = [{}]
    for chunk in chunks:
        rag.append({
            "id": chunk.id if chunk.id else "",
            "values": encoder_model.encode(chunk.metadata["text"]).tolist(),
            "metadata": chunk.metadata
        }
        )
    return rag
