from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.persistence import vector_store


class CapturingSession:
    statement = None

    def scalars(self, statement):
        self.statement = statement
        return self

    def all(self):
        return []


def test_vector_retrieval_filters_owner_report_and_owned_knowledge(monkeypatch) -> None:
    monkeypatch.setattr("app.persistence.vector_store.embed_query", lambda _: [0.0] * 1536)
    monkeypatch.setattr(
        vector_store,
        "get_settings",
        lambda: SimpleNamespace(
            ai_provider="gemini",
            gemini_embedding_model="gemini-embedding-001",
        ),
    )
    session = CapturingSession()
    owner_id = uuid4()
    report_id = uuid4()

    vector_store.retrieve_chunks(
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
    assert "evidence_chunks.embedding_provider" in sql
    assert "evidence_chunks.embedding_model" in sql
    assert owner_id in compiled.params.values()
    assert report_id in compiled.params.values()
    assert "gemini" in compiled.params.values()
    assert "gemini-embedding-001" in compiled.params.values()
