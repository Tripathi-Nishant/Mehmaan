"""bookings.dietary_notes: optional guest dietary needs / allergies (≤ 200 chars)

Revision ID: 0017_booking_dietary_notes
Revises: 0016_email_outbox
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_booking_dietary_notes"
down_revision = "0016_email_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("dietary_notes", sa.String(200)))


def downgrade() -> None:
    op.drop_column("bookings", "dietary_notes")
