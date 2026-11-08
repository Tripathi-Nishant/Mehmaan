"""add booking deadlines

Revision ID: 0008_booking_deadlines
Revises: 0007_media_listing
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_booking_deadlines"
down_revision = "0007_media_listing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("hold_expires_at", sa.DateTime(timezone=True)))
    op.add_column("bookings", sa.Column("host_reply_deadline", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("bookings", "host_reply_deadline")
    op.drop_column("bookings", "hold_expires_at")
