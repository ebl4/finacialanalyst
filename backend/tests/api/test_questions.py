from types import SimpleNamespace
from uuid import uuid4

from app.api.questions import ask_question
from app.api.schemas import QuestionRequest
from app.auth.dependencies import CurrentUser


class FakeSession:
    def __init__(self, report):
        self.report = report
        self.added = []
        self.committed = False

    def scalar(self, statement):
        return self.report

    def add(self, entity):
        self.added.append(entity)

    def commit(self):
        self.committed = True


def test_question_without_evidence_is_explicit_and_persisted(monkeypatch) -> None:
    report_id = uuid4()
    owner_id = uuid4()
    report = SimpleNamespace(id=report_id, owner_id=owner_id)
    session = FakeSession(report)
    monkeypatch.setattr(
        "app.api.questions.RetrievalAgent.invoke",
        lambda *args, **kwargs: [],
    )

    result = ask_question(
        report_id,
        QuestionRequest(question="What is the forecast?"),
        user=CurrentUser(id=owner_id, roles=frozenset({"analyst"})),
        session=session,
    )

    assert "not enough evidence" in result["answer"]
    assert result["citations"] == []
    assert session.committed is True
    assert session.added[0].question == "What is the forecast?"
    assert session.added[0].limitations
