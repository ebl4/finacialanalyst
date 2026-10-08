from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.persistence.vector_store import retrieve_chunks


class CapturingSession:
    statement = None

    def scalars(self, statement):
        self.statement = statement
        return self

    def all(self):
        return []


def test_vector_retrieval_filters_owner_report_and_owned_knowledge(monkeypatch) -> None:
    monkeypatch.setattr("app.persistence.vector_store.embed_query", lambda _: [0.0] * 1536)
    session = CapturingSession()
    owner_id = uuid4()
    report_id = uuid4()

    retrieve_chunks(
        session,
        owner_id=owner_id,
        report_id=report_id,
        question="What changed?",
    )

    compiled = session.statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "evidence_chunks.owner_id" in sql
    assert "evidence_chunks.report_id" in sql
    assert "evidence_chunks.knowledge_source_id IS NOT NULL" in sql
    assert owner_id in compiled.params.values()
    assert report_id in compiled.params.values()
