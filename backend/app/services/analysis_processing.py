import logging
from datetime import UTC, datetime
from uuid import UUID

from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.domain.states import (
    ANALYSIS_TRANSITIONS,
    RECOMMENDATION_TRANSITIONS,
    REPORT_TRANSITIONS,
    validate_transition,
)
from app.persistence.database import SessionLocal
from app.persistence.models import (
    AnalysisRun,
    AnalysisStatus,
    EvidenceChunk,
    Finding,
    Recommendation,
    RecommendationStatus,
    Report,
    ReportPage,
    ReportStatus,
    Role,
    User,
)
from app.persistence.object_storage import get_object_storage
from app.persistence.vector_store import index_chunks
from app.services.document_extraction import extract_pdf_pages
from app.workflows.graph import run_analysis

logger = logging.getLogger(__name__)


def _checkpoint_uri(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _split_page(page_number: int, text: str) -> list[tuple[int, str]]:
    normalized = " ".join(text.split())
    return [
        (page_number, normalized[offset : offset + 3000])
        for offset in range(0, len(normalized), 2600)
        if normalized[offset : offset + 3000].strip()
    ]


def process_report(report_id: UUID, run_id: UUID) -> None:
    try:
        _process_report(report_id, run_id)
    except Exception:
        logger.exception("Report analysis failed for report %s", report_id)
        with SessionLocal() as session:
            report = session.get(Report, report_id)
            run = session.get(AnalysisRun, run_id)
            if report:
                validate_transition(report.status, ReportStatus.FAILED.value, REPORT_TRANSITIONS)
                report.status = ReportStatus.FAILED
                report.error = "The report could not be analyzed. Review configuration and retry."
            if run:
                validate_transition(run.status, AnalysisStatus.FAILED.value, ANALYSIS_TRANSITIONS)
                run.status = AnalysisStatus.FAILED
                run.stage = "failed"
                run.error = "The report could not be analyzed. Review configuration and retry."
                run.finished_at = datetime.now(UTC)
            session.commit()


def _process_report(report_id: UUID, run_id: UUID) -> None:
    with SessionLocal() as session:
        report = session.get(Report, report_id)
        run = session.get(AnalysisRun, run_id)
        if not report or not run:
            raise RuntimeError("The report or analysis run no longer exists.")
        validate_transition(report.status, ReportStatus.PROCESSING.value, REPORT_TRANSITIONS)
        validate_transition(run.status, AnalysisStatus.RUNNING.value, ANALYSIS_TRANSITIONS)
        report.status = ReportStatus.PROCESSING
        run.status = AnalysisStatus.RUNNING
        run.stage = "extracting"
        run.error = None
        session.commit()

        contents = get_object_storage().get(report.object_key)
        pages = extract_pdf_pages(contents)
        session.execute(delete(EvidenceChunk).where(EvidenceChunk.report_id == report.id))
        session.execute(delete(ReportPage).where(ReportPage.report_id == report.id))
        for page_number, page_text in pages:
            session.add(ReportPage(report_id=report.id, page_number=page_number, text=page_text))
        chunks = [
            (page_number, content)
            for page_number, text in pages
            for page_number, content in _split_page(page_number, text)
        ]
        index_chunks(
            session,
            owner_id=report.owner_id,
            report_id=report.id,
            knowledge_source_id=None,
            pages=chunks,
        )
        session.commit()

        report_text = "\n\n".join(f"[Page {page_number}]\n{text}" for page_number, text in pages)
        with PostgresSaver.from_conn_string(
            _checkpoint_uri(get_settings().database_url)
        ) as checkpointer:
            checkpointer.setup()
            result = run_analysis(
                session,
                checkpointer,
                owner_id=report.owner_id,
                report_id=report.id,
                report_text=report_text,
                run_id=run.id,
            )
        validation = result["validation"]
        if not validation["accepted"]:
            raise ValueError(
                "Analysis validation rejected the result: " + "; ".join(validation["limitations"])
            )

        draft = result["draft"]
        evidence = result["evidence"]
        for finding in draft["findings"]:
            citations = _verified_citations(finding["citations"], evidence, report)
            session.add(
                Finding(
                    analysis_id=run.id,
                    title=finding["title"],
                    summary=finding["summary"],
                    uncertainty=finding.get("uncertainty"),
                    citations=citations,
                )
            )

        approver_id = _select_approver(session) if draft["recommendations"] else None
        for item in draft["recommendations"]:
            validate_transition(
                RecommendationStatus.DRAFT.value,
                RecommendationStatus.PENDING_APPROVAL.value,
                RECOMMENDATION_TRANSITIONS,
            )
            citations = _verified_citations(item["citations"], evidence, report)
            session.add(
                Recommendation(
                    analysis_id=run.id,
                    summary=item["summary"],
                    rationale=item["rationale"],
                    assumptions=item["assumptions"],
                    limitations=item["limitations"],
                    citations=citations,
                    sensitivity="requires_approval",
                    status=RecommendationStatus.PENDING_APPROVAL,
                    assigned_approver_id=approver_id,
                )
            )

        target_analysis_status = (
            AnalysisStatus.WAITING_FOR_APPROVAL
            if draft["recommendations"]
            else AnalysisStatus.COMPLETE
        )
        validate_transition(run.status, target_analysis_status.value, ANALYSIS_TRANSITIONS)
        validate_transition(report.status, ReportStatus.COMPLETE.value, REPORT_TRANSITIONS)
        run.status = target_analysis_status
        run.stage = "waiting_for_approval" if draft["recommendations"] else "complete"
        run.finished_at = datetime.now(UTC)
        report.status = ReportStatus.COMPLETE
        report.error = None
        session.commit()


def _verified_citations(citations: list[dict], evidence: list[dict], report: Report) -> list[dict]:
    verified: list[dict] = []
    for citation in citations:
        matches = [
            item
            for item in evidence
            if item["id"] == citation["source_id"]
            if item["page_number"] == citation["page"]
            and citation["excerpt"].casefold() in item["content"].casefold()
        ]
        if not matches:
            raise ValueError("A generated citation did not match its stated source page.")
        match = matches[0]
        if match["report_id"] == str(report.id):
            source_id, label = str(report.id), report.filename
        elif match["knowledge_source_id"]:
            source_id, label = match["knowledge_source_id"], "Knowledge source"
        else:
            raise ValueError("A generated citation references an unauthorized source.")
        verified.append(
            {
                "source_id": source_id,
                "chunk_id": match["id"],
                "label": label,
                "page": citation["page"],
                "excerpt": citation["excerpt"],
            }
        )
    if not verified:
        raise ValueError("A material finding or recommendation has no verifiable citation.")
    return verified


def _select_approver(session) -> UUID:
    approver = session.scalar(
        select(User)
        .where(User.active.is_(True), User.roles.contains([Role.APPROVER.value]))
        .order_by(User.id)
        .limit(1)
    )
    if not approver:
        raise RuntimeError("No active human approver is configured for sensitive recommendations.")
    return approver.id
