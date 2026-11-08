"""associate media with listings

Revision ID: 0007_media_listing
Revises: 0006_p1_media
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_media_listing"
down_revision = "0006_p1_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("media", sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_media_listing", "media", "listings", ["listing_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_media_listing", "media", type_="foreignkey")
    op.drop_column("media", "listing_id")
