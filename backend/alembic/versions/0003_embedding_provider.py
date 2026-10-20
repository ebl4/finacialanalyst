"""Track the provider and model used for evidence embeddings.

Revision ID: 0003_embedding_provider
Revises: 0002_analysis_questions
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_embedding_provider"
down_revision = "0002_analysis_questions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evidence_chunks",
        sa.Column(
            "embedding_provider",
            sa.String(length=20),
            server_default="openai",
            nullable=False,
        ),
    )
    op.add_column(
        "evidence_chunks",
        sa.Column(
            "embedding_model",
            sa.String(length=100),
            server_default="text-embedding-3-small",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("evidence_chunks", "embedding_model")
    op.drop_column("evidence_chunks", "embedding_provider")
