from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.database import Base


class Role(StrEnum):
    ANALYST = "analyst"
    APPROVER = "approver"


class ReportStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETE = "complete"
    FAILED = "failed"


class RecommendationStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


def new_id() -> UUID:
    return uuid4()


def now_utc() -> datetime:
    return datetime.now(UTC)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_id)
    owner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(1024), unique=True)
    content_digest: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"), default=ReportStatus.QUEUED
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    pages: Mapped[list["ReportPage"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(default=True)
    roles: Mapped[list[str]] = mapped_column(JSONB, default=list)


class ReportPage(Base):
    __tablename__ = "report_pages"
    __table_args__ = (UniqueConstraint("report_id", "page_number"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_id)
    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    report: Mapped[Report] = relationship(back_populates="pages")


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_id)
    owner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="available")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"
    __table_args__ = (
        CheckConstraint(
            "(report_id IS NOT NULL) <> (knowledge_source_id IS NOT NULL)",
            name="ck_evidence_chunk_one_source",
        ),
        Index(
            "ix_evidence_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_id)
    owner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), index=True, nullable=True
    )
    knowledge_source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True, nullable=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    embedding_provider: Mapped[str] = mapped_column(String(20))
    embedding_model: Mapped[str] = mapped_column(String(100))


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_id)
    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    requester_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"), default=AnalysisStatus.QUEUED
    )
    stage: Mapped[str] = mapped_column(String(80), default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class AnalysisQuestion(Base):
    __tablename__ = "analysis_questions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_id)
    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    requester_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    limitations: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_id)
    analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text)
    uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    analysis: Mapped[AnalysisRun] = relationship(back_populates="findings")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_id)
    analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    summary: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    assumptions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    limitations: Mapped[list[str]] = mapped_column(JSONB, default=list)
    citations: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    sensitivity: Mapped[str] = mapped_column(String(40))
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, name="recommendation_status"), default=RecommendationStatus.DRAFT
    )
    assigned_approver_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    analysis: Mapped[AnalysisRun] = relationship(back_populates="recommendations")
    events: Mapped[list["ApprovalEvent"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class ApprovalEvent(Base):
    __tablename__ = "approval_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_id)
    recommendation_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    outcome: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    recommendation: Mapped[Recommendation] = relationship(back_populates="events")
