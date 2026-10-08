from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.persistence.models import EvidenceChunk


def embed_texts(texts: list[str]) -> list[list[float]]:
    from langchain_openai import OpenAIEmbeddings

    settings = get_settings()
    if not settings.openai_api_key or not settings.openai_api_key.get_secret_value().strip():
        raise RuntimeError("OPENAI_API_KEY is required to create searchable document embeddings.")
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key.get_secret_value(),
    )
    return embeddings.embed_documents(texts)


def embed_query(text: str) -> list[float]:
    from langchain_openai import OpenAIEmbeddings

    settings = get_settings()
    if not settings.openai_api_key or not settings.openai_api_key.get_secret_value().strip():
        raise RuntimeError("OPENAI_API_KEY is required to search knowledge sources.")
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key.get_secret_value(),
    )
    return embeddings.embed_query(text)


def index_chunks(
    session: Session,
    *,
    owner_id: UUID,
    report_id: UUID | None,
    knowledge_source_id: UUID | None,
    pages: list[tuple[int | None, str]],
) -> None:
    vectors = embed_texts([text for _, text in pages])
    for (page_number, content), vector in zip(pages, vectors, strict=True):
        session.add(
            EvidenceChunk(
                owner_id=owner_id,
                report_id=report_id,
                knowledge_source_id=knowledge_source_id,
                page_number=page_number,
                content=content,
                embedding=vector,
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
    return list(session.scalars(statement.order_by(distance).limit(limit)).all())
