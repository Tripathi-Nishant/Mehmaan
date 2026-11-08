"""add Telegram webhook dedupe table

Revision ID: 0009_telegram_updates
Revises: 0008_booking_deadlines
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_telegram_updates"
down_revision = "0008_booking_deadlines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_updates",
        sa.Column("update_id", sa.BigInteger(), primary_key=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("telegram_updates")
