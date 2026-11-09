"""English listing copy: description_en, landmark_en (title_en exists since 0001)

Revision ID: 0014_listing_english_copy
Revises: 0013_listing_schedule
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_listing_english_copy"
down_revision = "0013_listing_schedule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("description_en", sa.Text()))
    op.add_column("listings", sa.Column("landmark_en", sa.String(200)))


def downgrade() -> None:
    op.drop_column("listings", "landmark_en")
    op.drop_column("listings", "description_en")
