import asyncio
import logging

from sqlalchemy import select

from app.domain.states import ANALYSIS_TRANSITIONS, REPORT_TRANSITIONS, validate_transition
from app.persistence.database import SessionLocal
from app.persistence.models import AnalysisRun, AnalysisStatus, Report, ReportStatus
from app.services.analysis_processing import process_report

logger = logging.getLogger(__name__)


def recover_interrupted_jobs() -> None:
    with SessionLocal() as session:
        interrupted = session.scalars(
            select(AnalysisRun).where(AnalysisRun.status == AnalysisStatus.RUNNING)
        ).all()
        for run in interrupted:
            validate_transition(run.status, AnalysisStatus.QUEUED.value, ANALYSIS_TRANSITIONS)
            run.status = AnalysisStatus.QUEUED
            run.stage = "queued"
            report = session.get(Report, run.report_id)
            if report:
                validate_transition(report.status, ReportStatus.QUEUED.value, REPORT_TRANSITIONS)
                report.status = ReportStatus.QUEUED
                report.error = None
        session.commit()


def process_next_job() -> bool:
    with SessionLocal() as session:
        run = session.scalar(
            select(AnalysisRun)
            .where(AnalysisRun.status == AnalysisStatus.QUEUED)
            .order_by(AnalysisRun.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not run:
            return False
        report_id, run_id = run.report_id, run.id
        validate_transition(run.status, AnalysisStatus.RUNNING.value, ANALYSIS_TRANSITIONS)
        run.status = AnalysisStatus.RUNNING
        run.stage = "starting"
        report = session.get(Report, report_id)
        if not report:
            run.status = AnalysisStatus.FAILED
            run.error = "The report record is missing."
            session.commit()
            return True
        validate_transition(report.status, ReportStatus.PROCESSING.value, REPORT_TRANSITIONS)
        report.status = ReportStatus.PROCESSING
        session.commit()
    process_report(report_id, run_id)
    return True


async def worker_loop() -> None:
    while True:
        try:
            worked = await asyncio.to_thread(process_next_job)
        except Exception:
            logger.exception("Analysis worker could not poll its durable job queue.")
            await asyncio.sleep(5)
            continue
        if not worked:
            await asyncio.sleep(2)
