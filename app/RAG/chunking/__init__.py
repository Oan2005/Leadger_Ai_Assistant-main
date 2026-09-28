"""
chunking
========

Responsible for splitting a parsed Docling document into RAG-ready
text chunks, attaching heading hierarchy and table metadata to each
chunk, and producing `Final_Document` objects ready for embedding.

Modules:
    - Parse_Documents: `Parse_Doc_for_Rag` — the main chunking entry point.
"""
