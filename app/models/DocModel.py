"""
DocModel
========

Defines `Final_Document`, the record type produced by the chunking
step and consumed by the embedding step.
"""

from dataclasses import dataclass


@dataclass
class Final_Document():
    """
    A single RAG chunk record.

    Attributes:
        id (str): Unique chunk identifier (`"{document_id}-{index}"`).
        values (list): Embedding vector. Empty when produced by
            `Parse_Doc_for_Rag`; populated later by `embedd_chunks`.
        metadata (dict): Chunk metadata — `source`, `headings`,
            `is_table`, and `text`.
    """
    id: str
    values: list
    metadata: dict

    def __init__(self, id, values, metadata):
        self.id = id
        self.values = values
        self.metadata = metadata
