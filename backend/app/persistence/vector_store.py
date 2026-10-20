from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_ai_api_key, get_settings
from app.persistence.models import EvidenceChunk


def _embedding_profile() -> tuple[str, str]:
    settings = get_settings()
    if settings.ai_provider == "gemini":
        return settings.ai_provider, settings.gemini_embedding_model
    return settings.ai_provider, settings.embedding_model


def _get_embeddings():
    settings = get_settings()
    api_key = get_ai_api_key(settings)
    if settings.ai_provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=api_key,
            output_dimensionality=1536,
        )

    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=settings.embedding_model, api_key=api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _get_embeddings().embed_documents(texts)


def embed_query(text: str) -> list[float]:
    return _get_embeddings().embed_query(text)


def index_chunks(
    session: Session,
    *,
    owner_id: UUID,
    report_id: UUID | None,
    knowledge_source_id: UUID | None,
    pages: list[tuple[int | None, str]],
) -> None:
    vectors = embed_texts([text for _, text in pages])
    embedding_provider, embedding_model = _embedding_profile()
    for (page_number, content), vector in zip(pages, vectors, strict=True):
        session.add(
            EvidenceChunk(
                owner_id=owner_id,
                report_id=report_id,
                knowledge_source_id=knowledge_source_id,
                page_number=page_number,
                content=content,
                embedding=vector,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
            )
        )
    session.flush()


def retrieve_chunks(
    session: Session,
    *,
    owner_id: UUID,
    question: str,
    report_id: UUID | None = None,
    limit: int = 6,
) -> list[EvidenceChunk]:
    query_vector = embed_query(question)
    distance = EvidenceChunk.embedding.cosine_distance(query_vector)
    statement = select(EvidenceChunk).where(EvidenceChunk.owner_id == owner_id)
    if report_id:
        statement = statement.where(
            (EvidenceChunk.report_id == report_id) | EvidenceChunk.knowledge_source_id.is_not(None)
        )
    embedding_provider, embedding_model = _embedding_profile()
    statement = statement.where(
        EvidenceChunk.embedding_provider == embedding_provider,
        EvidenceChunk.embedding_model == embedding_model,
    )
    return list(session.scalars(statement.order_by(distance).limit(limit)).all())
