from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.services.document_extraction import DocumentExtractionError, extract_pdf_pages


def test_rejects_non_pdf_bytes() -> None:
    with pytest.raises(DocumentExtractionError, match="unreadable"):
        extract_pdf_pages(b"not a PDF")


def test_rejects_pdf_without_extractable_text() -> None:
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(stream)

    with pytest.raises(DocumentExtractionError, match="No readable text"):
        extract_pdf_pages(stream.getvalue())
