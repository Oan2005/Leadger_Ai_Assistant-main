"""
embedding
=========

Loads the sentence-transformer embedding model and converts text
chunks into vector embeddings suitable for insertion into Pinecone.

Modules:
    - embedding_model: `embedd_chunks` — batch-embeds a list of chunks;
      also exposes the shared `embedding_model` instance used at query
      time (see `app.vector_database.query`).
"""
