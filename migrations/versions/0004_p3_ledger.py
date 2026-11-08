"""add ledger and booking money columns

Revision ID: 0004_p3_ledger
Revises: 0003_p3_bookings
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_p3_ledger"
down_revision = "0003_p3_bookings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bookings", sa.Column("commission_paise", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "bookings", sa.Column("host_payout_paise", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_table(
        "ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "booking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bookings.id"),
            nullable=False,
        ),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hosts.id")),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("ledger_entries")
    op.drop_column("bookings", "host_payout_paise")
    op.drop_column("bookings", "commission_paise")
