"""At most one REFUND ledger row per booking (double cancel/decline can't refund twice)

Revision ID: 0015_one_refund_per_booking
Revises: 0014_listing_english_copy
"""

import sqlalchemy as sa
from alembic import op

revision = "0015_one_refund_per_booking"
down_revision = "0014_listing_english_copy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_ledger_one_refund_per_booking",
        "ledger_entries",
        ["booking_id"],
        unique=True,
        postgresql_where=sa.text("type = 'REFUND'"),
    )


def downgrade() -> None:
    op.drop_index("uq_ledger_one_refund_per_booking", table_name="ledger_entries")
