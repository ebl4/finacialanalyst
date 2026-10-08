import pytest

from app.domain.states import (
    ANALYSIS_TRANSITIONS,
    REPORT_TRANSITIONS,
    validate_transition,
)
from app.persistence.models import AnalysisStatus, ReportStatus
from app.services.report_upload import ReportUploadError, validate_pdf_upload


def test_accepts_nonempty_pdf_under_configured_limit() -> None:
    validate_pdf_upload("annual-report.pdf", "application/pdf", b"%PDF-content", 1024)


@pytest.mark.parametrize(
    ("filename", "content_type", "contents", "limit", "message"),
    [
        ("report.docx", "application/pdf", b"data", 100, "Only PDF"),
        ("report.pdf", "text/plain", b"data", 100, "must be a PDF"),
        ("report.pdf", "application/pdf", b"x" * 5, 4, "upload limit"),
        ("report.pdf", "application/pdf", b"", 100, "empty"),
    ],
)
def test_rejects_invalid_report_uploads(filename, content_type, contents, limit, message) -> None:
    with pytest.raises(ReportUploadError, match=message):
        validate_pdf_upload(filename, content_type, contents, limit)


def test_state_transitions_allow_worker_recovery_but_reject_complete_requeue() -> None:
    assert (
        validate_transition(
            ReportStatus.PROCESSING,
            ReportStatus.QUEUED.value,
            REPORT_TRANSITIONS,
        )
        == "queued"
    )
    with pytest.raises(ValueError, match="Invalid state transition"):
        validate_transition(
            AnalysisStatus.COMPLETE,
            AnalysisStatus.QUEUED.value,
            ANALYSIS_TRANSITIONS,
        )
