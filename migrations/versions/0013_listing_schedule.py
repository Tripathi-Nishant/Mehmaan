"""listing schedule + capacity fields; drop per-host cancellation_rule (policy is fixed)

Revision ID: 0013_listing_schedule
Revises: 0012_location_pin
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_listing_schedule"
down_revision = "0012_location_pin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("duration_min", sa.Integer()))
    op.add_column("listings", sa.Column("max_guests", sa.Integer()))
    op.add_column("listings", sa.Column("available_weekdays", postgresql.ARRAY(sa.Integer())))
    op.add_column("listings", sa.Column("start_time_local", sa.Time()))
    op.add_column("listings", sa.Column("food_type", sa.String(20)))
    op.add_column("listings", sa.Column("published_at", sa.DateTime(timezone=True)))
    op.drop_column("listings", "cancellation_rule")


def downgrade() -> None:
    op.add_column("listings", sa.Column("cancellation_rule", sa.String(300)))
    op.drop_column("listings", "published_at")
    op.drop_column("listings", "food_type")
    op.drop_column("listings", "start_time_local")
    op.drop_column("listings", "available_weekdays")
    op.drop_column("listings", "max_guests")
    op.drop_column("listings", "duration_min")
