from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.approvals import decide_recommendation
from app.api.schemas import DecisionRequest
from app.auth.dependencies import CurrentUser
from app.persistence.models import AnalysisStatus, RecommendationStatus


class FakeSession:
    def __init__(self, recommendation, run=None):
        self.recommendation = recommendation
        self.run = run
        self.added = []
        self.commits = 0
        self.scalar_calls = 0

    def scalar(self, statement):
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            return self.recommendation
        return None

    def add(self, entity):
        self.added.append(entity)

    def get(self, model, entity_id):
        return self.run

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        return None


def test_assigned_approver_records_decision_and_completes_analysis() -> None:
    approver_id = uuid4()
    recommendation = SimpleNamespace(
        id=uuid4(),
        analysis_id=uuid4(),
        assigned_approver_id=approver_id,
        status=RecommendationStatus.PENDING_APPROVAL,
    )
    run = SimpleNamespace(
        id=recommendation.analysis_id,
        status=AnalysisStatus.WAITING_FOR_APPROVAL,
        stage="waiting_for_approval",
    )
    session = FakeSession(recommendation, run)

    result = decide_recommendation(
        recommendation.id,
        DecisionRequest(outcome="approved", reason="Reviewed supporting data."),
        user=CurrentUser(id=approver_id, roles=frozenset({"approver"})),
        session=session,
    )

    assert recommendation.status == RecommendationStatus.APPROVED
    assert run.status == AnalysisStatus.COMPLETE
    assert result["decision"] == "approved"
    assert session.added[0].actor_id == approver_id
    assert session.commits == 1


def test_unauthorized_approval_is_denied_and_audited() -> None:
    analyst_id = uuid4()
    recommendation = SimpleNamespace(
        id=uuid4(),
        assigned_approver_id=uuid4(),
        status=RecommendationStatus.PENDING_APPROVAL,
    )
    session = FakeSession(recommendation)

    with pytest.raises(HTTPException) as error:
        decide_recommendation(
            recommendation.id,
            DecisionRequest(outcome="approved"),
            user=CurrentUser(id=analyst_id, roles=frozenset({"analyst"})),
            session=session,
        )

    assert error.value.status_code == 403
    assert recommendation.status == RecommendationStatus.PENDING_APPROVAL
    assert session.added[0].outcome == "denied"
    assert session.commits == 1


def test_approver_not_assigned_to_recommendation_is_denied_and_audited() -> None:
    approver_id = uuid4()
    recommendation = SimpleNamespace(
        id=uuid4(),
        assigned_approver_id=uuid4(),
        status=RecommendationStatus.PENDING_APPROVAL,
    )
    session = FakeSession(recommendation)

    with pytest.raises(HTTPException) as error:
        decide_recommendation(
            recommendation.id,
            DecisionRequest(outcome="approved"),
            user=CurrentUser(id=approver_id, roles=frozenset({"approver"})),
            session=session,
        )

    assert error.value.status_code == 404
    assert recommendation.status == RecommendationStatus.PENDING_APPROVAL
    assert session.added[0].actor_id == approver_id
    assert session.added[0].outcome == "denied"
