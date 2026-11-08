"""add payouts

Revision ID: 0005_p5_payouts
Revises: 0004_p3_ledger
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_p5_payouts"
down_revision = "0004_p3_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hosts.id"), nullable=False
        ),
        sa.Column(
            "booking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bookings.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("payouts")
