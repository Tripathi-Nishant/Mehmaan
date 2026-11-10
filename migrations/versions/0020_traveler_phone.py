"""Store an optional traveler phone number for host booking notifications."""

import sqlalchemy as sa
from alembic import op


revision = "0020_traveler_phone"
down_revision = "0019_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("travelers", sa.Column("phone", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("travelers", "phone")
