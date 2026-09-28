"""
Parse_Documents
================

Splits a Docling document object into RAG-ready chunks using a
`HybridChunker`, cleans each chunk's text, and wraps the result in
`Final_Document` objects that carry the metadata needed for vector
storage (source file, heading hierarchy, table flag, cleaned text).

Dependencies:
    - docling.chunking.HybridChunker
    - app.ingestion.clean_text.clean_text
    - app.models.DocModel.Final_Document

Input:
    - objects: a Docling `DoclingDocument` (as returned by
      `app.ingestion.extraction_process.extract_to_objects`).
    - file_path: original path/filename of the source document, used
      to populate the "source" metadata field.

Output:
    - list[Final_Document]: one entry per chunk, with empty `values`
      (embeddings are filled in later by `app.embedding.embedding_model`).
"""

from docling.chunking import HybridChunker
from pathlib import Path
import uuid
from app.RAG.ingestion.preprocessing import clean_records
from app.models.DocModel import Final_Document


def Parse_Doc_for_Rag(objects, file_path: str,company_id:str):
    """
    Chunk a Docling document into RAG-ready `Final_Document` objects.

    Each chunk is produced by a `HybridChunker` (tokenizer matched to the
    downstream embedding model), then cleaned via `clean_text` and tagged
    with its heading hierarchy and whether it originated from a table.

    Args:
        objects: The Docling document object to chunk (output of
            `extract_to_objects`).
        file_path (str): Path/filename of the original source document.
            Only the file name (`Path(file_path).name`) is stored in
            chunk metadata.

    Returns:
        list[Final_Document]: Chunk objects with `id`, empty `values`
        (to be filled by the embedding step), and `metadata` containing
        `source`, `headings`, `is_table`, and `text`.
    """
    document_id = str(uuid.uuid4())

    chunker = HybridChunker(
        tokenizer="sentence-transformers/all-MiniLM-L6-v2",
        max_tokens=256
    )

    doc_chunk = chunker.chunk(objects)
    vectors = []
    for index, chunk in enumerate(doc_chunk):
        chunk_records = chunker.serialize(chunk)
        cleaned_chunk_text = clean_records(chunk_records)
        heading_hierarchy = chunk.meta.headings if chunk.meta.headings else ["Root"]

        Object_chunk = vectors.append(Final_Document(
            id=f"{document_id}-{index}",
            values=[],
            metadata={
                "company_id": str(company_id),
                "document_id": document_id,
                "chunk_index": index,
                "source": Path(file_path).name,
                "headings": " > ".join(heading_hierarchy),
                "status":"ready",
                "text": cleaned_chunk_text,
            }
        ))

    return {
        "vectors":vectors,
        "document_id":document_id
    }
