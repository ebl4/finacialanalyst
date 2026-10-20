from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.agents import clients
from app.core.config import get_ai_api_key
from app.persistence import vector_store


def test_get_ai_api_key_uses_selected_provider() -> None:
    settings = SimpleNamespace(
        ai_provider="gemini",
        openai_api_key=SecretStr("openai-key"),
        google_api_key=SecretStr("google-key"),
    )

    assert get_ai_api_key(settings) == "google-key"


def test_get_ai_api_key_reports_selected_provider_key_name() -> None:
    settings = SimpleNamespace(
        ai_provider="gemini",
        openai_api_key=SecretStr("openai-key"),
        google_api_key=None,
    )

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        get_ai_api_key(settings)


def test_gemini_embeddings_use_database_vector_dimension(monkeypatch) -> None:
    captured = {}

    class FakeEmbeddings:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

        def embed_documents(self, texts):
            return [[0.0] * 1536 for _ in texts]

        def embed_query(self, text):
            return [0.0] * 1536

    google_module = ModuleType("langchain_google_genai")
    google_module.GoogleGenerativeAIEmbeddings = FakeEmbeddings
    monkeypatch.setitem(__import__("sys").modules, "langchain_google_genai", google_module)
    monkeypatch.setattr(
        vector_store,
        "get_settings",
        lambda: SimpleNamespace(
            ai_provider="gemini",
            google_api_key=SecretStr("google-key"),
            gemini_embedding_model="gemini-embedding-001",
        ),
    )

    vectors = vector_store.embed_texts(["report text"])
    query_vector = vector_store.embed_query("revenue")

    assert len(vectors[0]) == len(query_vector) == 1536
    assert captured == {
        "model": "gemini-embedding-001",
        "google_api_key": "google-key",
        "output_dimensionality": 1536,
    }


def test_indexed_chunks_record_embedding_provider_and_model(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added = []
            self.flushed = False

        def add(self, entity) -> None:
            self.added.append(entity)

        def flush(self) -> None:
            self.flushed = True

    monkeypatch.setattr(vector_store, "embed_texts", lambda _: [[0.0] * 1536])
    monkeypatch.setattr(
        vector_store,
        "get_settings",
        lambda: SimpleNamespace(
            ai_provider="gemini",
            gemini_embedding_model="gemini-embedding-001",
        ),
    )
    session = FakeSession()

    vector_store.index_chunks(
        session,
        owner_id=uuid4(),
        report_id=uuid4(),
        knowledge_source_id=None,
        pages=[(1, "revenue data")],
    )

    assert session.flushed
    assert session.added[0].embedding_provider == "gemini"
    assert session.added[0].embedding_model == "gemini-embedding-001"


def test_gemini_chat_model_supports_structured_agent_outputs(monkeypatch) -> None:
    from app.agents.schemas import AnalysisDraft

    settings = SimpleNamespace(
        ai_provider="gemini",
        google_api_key=SecretStr("google-key"),
        gemini_model="gemini-2.5-flash",
    )
    monkeypatch.setattr(clients, "get_settings", lambda: settings)
    clients.get_chat_model.cache_clear()

    try:
        model = clients.get_chat_model()

        assert model.model == "gemini-2.5-flash"
        assert model.with_structured_output(AnalysisDraft) is not None
    finally:
        clients.get_chat_model.cache_clear()
