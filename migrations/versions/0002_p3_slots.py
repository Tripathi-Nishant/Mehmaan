"""add listing slots

Revision ID: 0002_p3_slots
Revises: 0001_p1_onboarding
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_p3_slots"
down_revision = "0001_p1_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("booked_count", sa.Integer(), nullable=False),
        sa.UniqueConstraint("listing_id", "starts_at"),
    )


def downgrade() -> None:
    op.drop_table("slots")
