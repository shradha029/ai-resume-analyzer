"""PDF validation and text extraction (PyMuPDF)."""
import re
import unicodedata

import pymupdf

MAX_PAGES = 15
MIN_TEXT_CHARS = 30


class PdfProcessingError(Exception):
    """Raised with a user-safe message when a PDF cannot be processed."""


def extract_text(content: bytes) -> tuple[str, int]:
    """Return (text, page_count) or raise PdfProcessingError."""
    if not content.startswith(b"%PDF-"):
        raise PdfProcessingError("File is not a valid PDF.")
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
    except Exception:
        raise PdfProcessingError("The PDF is corrupted and could not be opened.")
    try:
        if doc.needs_pass or doc.is_encrypted:
            raise PdfProcessingError("The PDF is password-protected. Remove the password and upload again.")
        pages = doc.page_count
        if pages == 0:
            raise PdfProcessingError("The PDF has no pages.")
        if pages > MAX_PAGES:
            raise PdfProcessingError(f"The PDF has {pages} pages. Maximum allowed is {MAX_PAGES}.")
        try:
            text = "\n".join(page.get_text("text", sort=True) for page in doc)
        except Exception:
            raise PdfProcessingError("The PDF is corrupted and its text could not be read.")
    finally:
        doc.close()

    text = unicodedata.normalize("NFKC", text).replace("\xa0", " ")
    if len(re.sub(r"\s", "", text)) < MIN_TEXT_CHARS:
        raise PdfProcessingError(
            "No selectable text found. This looks like an empty or scanned PDF. "
            "Scanned (image-only) resumes are not supported in this version; upload a text-based PDF."
        )
    return text, pages
