class ReportUploadError(ValueError):
    pass


def validate_pdf_upload(filename: str, content_type: str, contents: bytes, max_bytes: int) -> None:
    if not filename.strip() or not filename.lower().endswith(".pdf"):
        raise ReportUploadError("Only PDF financial reports are supported.")
    if content_type != "application/pdf":
        raise ReportUploadError("The uploaded report must be a PDF.")
    if len(contents) > max_bytes:
        raise ReportUploadError("The report exceeds the configured upload limit.")
    if not contents:
        raise ReportUploadError("The uploaded report is empty.")
