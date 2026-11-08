"""add listing location and cancellation fields

Revision ID: 0011_listing_location_fields
Revises: 0010_reviews
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_listing_location_fields"
down_revision = "0010_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("location_lat", sa.Float()))
    op.add_column("listings", sa.Column("location_lng", sa.Float()))
    op.add_column("listings", sa.Column("landmark", sa.String(200)))
    op.add_column("listings", sa.Column("cancellation_rule", sa.String(300)))


def downgrade() -> None:
    op.drop_column("listings", "cancellation_rule")
    op.drop_column("listings", "landmark")
    op.drop_column("listings", "location_lng")
    op.drop_column("listings", "location_lat")
