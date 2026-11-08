"""add media blobs

Revision ID: 0006_p1_media
Revises: 0005_p5_payouts
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_p1_media"
down_revision = "0005_p5_payouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("media")
