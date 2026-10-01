"""
extraction_process
===================

Document extraction helpers used to turn a raw uploaded file into
either a Docling document object (primary path, used by the
`/upload` API endpoint) or plain text (legacy per-format helpers,
currently unused by the active pipeline but preserved as-is).

Dependencies:
    - docling.document_converter.DocumentConverter
    - PyPDF2
    - docx (python-docx)
"""


from docling.document_converter import DocumentConverter
import logging

logger = logging.getLogger(__name__)

def extract_to_objects(file_path: str):
    """
    Extract a document into a Docling document object.

    This is the primary extraction path used by the `/upload` API
    endpoint; its output is passed directly into
    `app.chunking.Parse_Documents.Parse_Doc_for_Rag`.

    Args:
        file_path (str): Path to the input document.

    Returns:
        Document | None: Extracted document object, or None if extraction fails.
    """
    try:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        pages = len(result.document.pages)

        return result.document

    except Exception:
        logger.exception("Document extraction failed")
        return None

