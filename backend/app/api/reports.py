import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import CurrentUser, get_current_user
from app.core.config import get_settings
from app.persistence.database import get_db
from app.persistence.models import (
    AnalysisRun,
    AnalysisStatus,
    Recommendation,
    RecommendationStatus,
    Report,
    ReportStatus,
    Role,
    new_id,
)
from app.persistence.object_storage import (
    ObjectStorage,
    StorageNotConfigured,
    get_object_storage,
)
from app.services.report_upload import ReportUploadError, validate_pdf_upload

router = APIRouter(tags=["reports"])


def require_storage() -> ObjectStorage:
    try:
        return get_object_storage()
    except StorageNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/reports", status_code=status.HTTP_202_ACCEPTED)
async def submit_report(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
    storage: ObjectStorage = Depends(require_storage),
):
    if Role.ANALYST.value not in user.roles:
        raise HTTPException(status_code=403, detail="Analyst permission is required.")
    filename = (file.filename or "").strip()
    contents = await file.read(get_settings().max_upload_bytes + 1)
    try:
        validate_pdf_upload(
            filename, file.content_type or "", contents, get_settings().max_upload_bytes
        )
    except ReportUploadError as exc:
        code = 413 if "upload limit" in str(exc) else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc

    report_id = new_id()
    analysis_id = new_id()
    object_key = f"reports/{user.id}/{report_id}.pdf"
    try:
        storage.put(object_key, contents, "application/pdf")
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    report = Report(
        id=report_id,
        owner_id=user.id,
        filename=filename[:255],
        content_type="application/pdf",
        object_key=object_key,
        content_digest=hashlib.sha256(contents).hexdigest(),
        byte_size=len(contents),
        status=ReportStatus.QUEUED,
    )
    run = AnalysisRun(
        id=analysis_id,
        report_id=report_id,
        requester_id=user.id,
        status=AnalysisStatus.QUEUED,
        stage="queued",
    )
    session.add_all([report, run])
    session.commit()
    return {
        "id": report.id,
        "filename": report.filename,
        "status": report.status,
        "submitted_at": report.submitted_at,
        "analysis_status": run.status,
    }


@router.get("/reports")
def list_reports(user: CurrentUser = Depends(get_current_user), session: Session = Depends(get_db)):
    reports = session.scalars(
        select(Report).where(Report.owner_id == user.id).order_by(Report.submitted_at.desc())
    )
    return [
        {
            "id": report.id,
            "filename": report.filename,
            "status": report.status,
            "submitted_at": report.submitted_at,
            "error": report.error,
        }
        for report in reports
    ]


@router.get("/reports/{report_id}")
def get_report(
    report_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    report = session.scalar(
        select(Report).where(Report.id == report_id, Report.owner_id == user.id)
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {
        "id": report.id,
        "filename": report.filename,
        "status": report.status,
        "submitted_at": report.submitted_at,
        "error": report.error,
    }


@router.get("/reports/{report_id}/analysis")
def get_analysis(
    report_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    report = session.scalar(
        select(Report)
        .options(selectinload(Report.pages))
        .where(Report.id == report_id, Report.owner_id == user.id)
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    run = session.scalar(
        select(AnalysisRun)
        .options(
            selectinload(AnalysisRun.findings),
            selectinload(AnalysisRun.recommendations).selectinload(Recommendation.events),
        )
        .where(AnalysisRun.report_id == report_id)
    )
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return {
        "report_id": report.id,
        "status": run.status,
        "findings": [
            {
                "id": item.id,
                "title": item.title,
                "summary": item.summary,
                "uncertainty": item.uncertainty,
                "citations": item.citations,
            }
            for item in run.findings
        ],
        "recommendations": [
            {
                "id": item.id,
                "summary": item.summary,
                "rationale": item.rationale,
                "assumptions": item.assumptions,
                "limitations": item.limitations,
                "sensitivity": item.sensitivity,
                "status": item.status,
                "citations": item.citations,
                "decisions": [
                    {
                        "outcome": event.outcome,
                        "reason": event.reason,
                        "created_at": event.created_at,
                    }
                    for event in item.events
                ],
            }
            for item in run.recommendations
        ],
        "limitations": [run.error] if run.error else [],
    }


@router.get("/reports/{report_id}/citations/{page_number}")
def get_report_page(
    report_id: UUID,
    page_number: int,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    report = session.scalar(select(Report).where(Report.id == report_id))
    is_owner = report is not None and report.owner_id == user.id
    is_assigned_approver = (
        session.scalar(
            select(Recommendation.id)
            .join(AnalysisRun, Recommendation.analysis_id == AnalysisRun.id)
            .where(
                AnalysisRun.report_id == report_id,
                Recommendation.assigned_approver_id == user.id,
                Recommendation.status.in_(
                    [
                        RecommendationStatus.PENDING_APPROVAL,
                        RecommendationStatus.APPROVED,
                        RecommendationStatus.REJECTED,
                    ]
                ),
            )
            .limit(1)
        )
        is not None
    )
    if not report or not (is_owner or is_assigned_approver):
        raise HTTPException(status_code=404, detail="Source not found.")
    from app.persistence.models import ReportPage

    page = session.scalar(
        select(ReportPage).where(
            ReportPage.report_id == report_id, ReportPage.page_number == page_number
        )
    )
    if not page:
        raise HTTPException(status_code=404, detail="Source passage not found.")
    return {
        "source_id": report.id,
        "label": report.filename,
        "page": page_number,
        "text": page.text,
    }
