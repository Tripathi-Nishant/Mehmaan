"""add completed booking reviews

Revision ID: 0010_reviews
Revises: 0009_telegram_updates
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_reviews"
down_revision = "0009_telegram_updates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "booking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bookings.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("author_role", sa.String(20), nullable=False),
        sa.Column("warmth", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("reviews")
