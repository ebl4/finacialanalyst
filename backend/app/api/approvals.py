from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import DecisionRequest
from app.auth.dependencies import CurrentUser, get_current_user
from app.domain.states import ANALYSIS_TRANSITIONS, RECOMMENDATION_TRANSITIONS, validate_transition
from app.persistence.database import get_db
from app.persistence.models import (
    AnalysisRun,
    AnalysisStatus,
    ApprovalEvent,
    Recommendation,
    RecommendationStatus,
    Role,
)

router = APIRouter(tags=["approvals"])


def _require_approver(user: CurrentUser) -> None:
    if Role.APPROVER.value not in user.roles:
        raise HTTPException(status_code=403, detail="Approver permission is required.")


def _record_denied_attempt(
    session: Session, recommendation: Recommendation, user: CurrentUser
) -> None:
    session.add(
        ApprovalEvent(
            recommendation_id=recommendation.id,
            actor_id=user.id,
            outcome="denied",
            reason="Unauthorized approval attempt.",
            created_at=datetime.now(UTC),
        )
    )
    session.commit()


@router.get("/approvals")
def list_approvals(
    user: CurrentUser = Depends(get_current_user), session: Session = Depends(get_db)
):
    _require_approver(user)
    recommendations = session.scalars(
        select(Recommendation)
        .where(
            Recommendation.assigned_approver_id == user.id,
            Recommendation.status == RecommendationStatus.PENDING_APPROVAL,
        )
        .order_by(Recommendation.id)
    )
    return [
        {
            "id": item.id,
            "summary": item.summary,
            "rationale": item.rationale,
            "assumptions": item.assumptions,
            "limitations": item.limitations,
            "sensitivity": item.sensitivity,
            "status": item.status,
            "citations": item.citations,
        }
        for item in recommendations
    ]


@router.post("/recommendations/{recommendation_id}/decision")
def decide_recommendation(
    recommendation_id: UUID,
    request: DecisionRequest,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    recommendation = session.scalar(
        select(Recommendation).where(Recommendation.id == recommendation_id).with_for_update()
    )
    if Role.APPROVER.value not in user.roles:
        if recommendation:
            _record_denied_attempt(session, recommendation, user)
        raise HTTPException(status_code=403, detail="Approver permission is required.")
    if request.outcome not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Outcome must be approved or rejected.")
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    if recommendation.assigned_approver_id != user.id:
        _record_denied_attempt(session, recommendation, user)
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    if recommendation.status != RecommendationStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=409, detail="Recommendation is no longer pending.")

    target_status = (
        RecommendationStatus.APPROVED
        if request.outcome == "approved"
        else RecommendationStatus.REJECTED
    )
    validate_transition(
        recommendation.status,
        target_status.value,
        RECOMMENDATION_TRANSITIONS,
    )
    recommendation.status = target_status
    session.add(
        ApprovalEvent(
            recommendation_id=recommendation.id,
            actor_id=user.id,
            outcome=request.outcome,
            reason=request.reason,
            created_at=datetime.now(UTC),
        )
    )
    run = session.get(AnalysisRun, recommendation.analysis_id)
    if run:
        pending_count = session.scalar(
            select(Recommendation.id)
            .where(
                Recommendation.analysis_id == run.id,
                Recommendation.id != recommendation.id,
                Recommendation.status == RecommendationStatus.PENDING_APPROVAL,
            )
            .limit(1)
        )
        if pending_count is None:
            validate_transition(
                run.status,
                AnalysisStatus.COMPLETE.value,
                ANALYSIS_TRANSITIONS,
            )
            run.status = AnalysisStatus.COMPLETE
            run.stage = "complete"
    session.commit()
    session.refresh(recommendation)
    return {
        "id": recommendation.id,
        "status": recommendation.status,
        "decision": request.outcome,
        "decided_at": datetime.now(UTC),
    }
