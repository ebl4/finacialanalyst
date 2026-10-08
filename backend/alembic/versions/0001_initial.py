"""Create initial financial analysis tables.

Revision ID: 0001_initial
Revises:
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("roles", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("object_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("content_digest", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("QUEUED", "PROCESSING", "COMPLETE", "FAILED", name="report_status"),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "report_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint("report_id", "page_number"),
    )
    op.create_table(
        "evidence_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "knowledge_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.CheckConstraint(
            "(report_id IS NOT NULL) <> (knowledge_source_id IS NOT NULL)",
            name="ck_evidence_chunk_one_source",
        ),
    )
    op.create_table(
        "analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "RUNNING",
                "WAITING_FOR_APPROVAL",
                "COMPLETE",
                "FAILED",
                name="analysis_status",
            ),
            nullable=False,
        ),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=True),
        sa.Column("citations", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False),
        sa.Column("limitations", postgresql.JSONB(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False),
        sa.Column("sensitivity", sa.String(40), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PENDING_APPROVAL",
                "APPROVED",
                "REJECTED",
                "SUPERSEDED",
                name="recommendation_status",
            ),
            nullable=False,
        ),
        sa.Column("assigned_approver_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_table(
        "approval_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recommendation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recommendations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False),
    )
    for table, column in (
        ("reports", "owner_id"),
        ("knowledge_sources", "owner_id"),
        ("report_pages", "report_id"),
        ("evidence_chunks", "owner_id"),
        ("evidence_chunks", "report_id"),
        ("evidence_chunks", "knowledge_source_id"),
        ("analysis_runs", "report_id"),
        ("analysis_runs", "requester_id"),
        ("findings", "analysis_id"),
        ("recommendations", "analysis_id"),
        ("recommendations", "assigned_approver_id"),
        ("approval_events", "recommendation_id"),
    ):
        op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_index(
        "ix_evidence_chunks_embedding_hnsw",
        "evidence_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("approval_events")
    op.drop_table("recommendations")
    op.drop_table("findings")
    op.drop_table("analysis_runs")
    op.drop_table("evidence_chunks")
    op.drop_table("report_pages")
    op.drop_table("knowledge_sources")
    op.drop_table("reports")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS recommendation_status")
    op.execute("DROP TYPE IF EXISTS analysis_status")
    op.execute("DROP TYPE IF EXISTS report_status")
