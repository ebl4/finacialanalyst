from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.persistence.database import get_db
from app.persistence.models import EvidenceChunk, KnowledgeSource
from app.persistence.vector_store import index_chunks

router = APIRouter(tags=["knowledge"])


class KnowledgeSourceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=250_000)


@router.post("/knowledge-sources", status_code=201)
def create_knowledge_source(
    request: KnowledgeSourceRequest,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Knowledge source content is empty.")
    source = KnowledgeSource(
        owner_id=user.id,
        name=request.name.strip(),
        source_type="text",
        status="indexing",
    )
    session.add(source)
    session.flush()
    chunks = [
        (None, content[offset : offset + 3000])
        for offset in range(0, len(content), 2600)
        if content[offset : offset + 3000].strip()
    ]
    try:
        index_chunks(
            session,
            owner_id=user.id,
            report_id=None,
            knowledge_source_id=source.id,
            pages=chunks,
        )
        source.status = "available"
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"id": source.id, "name": source.name, "status": source.status}


@router.get("/knowledge-sources/{source_id}/citations/{chunk_id}")
def get_knowledge_citation(
    source_id: str,
    chunk_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    from uuid import UUID

    try:
        parsed_source_id = UUID(source_id)
        parsed_chunk_id = UUID(chunk_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Source passage not found.") from exc
    chunk = session.scalar(
        select(EvidenceChunk)
        .join(KnowledgeSource, EvidenceChunk.knowledge_source_id == KnowledgeSource.id)
        .where(
            EvidenceChunk.id == parsed_chunk_id,
            KnowledgeSource.id == parsed_source_id,
            KnowledgeSource.owner_id == user.id,
        )
    )
    if not chunk:
        raise HTTPException(status_code=404, detail="Source passage not found.")
    source = session.get(KnowledgeSource, parsed_source_id)
    return {
        "label": source.name,
        "page": None,
        "text": chunk.content,
    }
