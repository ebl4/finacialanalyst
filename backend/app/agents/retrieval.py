from uuid import UUID

from sqlalchemy.orm import Session

from app.persistence.vector_store import retrieve_chunks


class RetrievalAgent:
    def invoke(
        self, session: Session, *, owner_id: UUID, report_id: UUID | None, question: str
    ) -> list[dict]:
        chunks = retrieve_chunks(session, owner_id=owner_id, report_id=report_id, question=question)
        return [
            {
                "id": str(chunk.id),
                "report_id": str(chunk.report_id) if chunk.report_id else None,
                "knowledge_source_id": (
                    str(chunk.knowledge_source_id) if chunk.knowledge_source_id else None
                ),
                "page_number": chunk.page_number,
                "content": chunk.content,
            }
            for chunk in chunks
        ]
