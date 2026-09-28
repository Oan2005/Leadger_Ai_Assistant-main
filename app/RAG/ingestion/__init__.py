"""
ingestion
=========

Handles raw document extraction (via Docling, and legacy PDF/TXT/DOCX
readers) and text cleaning prior to chunking.

Modules:
    - extraction_process: `extract_to_objects` (primary Docling-based
      extraction used by the `/upload` endpoint) plus legacy per-format
      extraction helpers (`extract_pdf`, `extract_txt`, `extract_word`).
    - clean_text: `clean_text` — lightweight text cleanup applied to
      each chunk before it is stored.
"""
