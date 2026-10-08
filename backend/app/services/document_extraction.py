from io import BytesIO

from pypdf import PdfReader


class DocumentExtractionError(ValueError):
    pass


def extract_pdf_pages(contents: bytes) -> list[tuple[int, str]]:
    try:
        reader = PdfReader(BytesIO(contents), strict=True)
        pages = [
            (page_number, page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, 1)
        ]
    except Exception as exc:
        raise DocumentExtractionError("The PDF is unreadable or incomplete.") from exc
    if not pages or not any(text.strip() for _, text in pages):
        raise DocumentExtractionError("No readable text was found in this PDF.")
    return pages
