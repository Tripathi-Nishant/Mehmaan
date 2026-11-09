"""location pin: accuracy, private gate photo, Hindi landmark; drop exact_address

Revision ID: 0012_location_pin
Revises: 0011_listing_location_fields
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_location_pin"
down_revision = "0011_listing_location_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("location_accuracy_m", sa.Float()))
    op.add_column(
        "listings", sa.Column("gate_photo_media_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_listing_gate_photo", "listings", "media", ["gate_photo_media_id"], ["id"]
    )
    op.alter_column("listings", "landmark", new_column_name="landmark_hi")
    op.drop_column("listings", "exact_address")


def downgrade() -> None:
    op.add_column("listings", sa.Column("exact_address", sa.Text()))
    op.alter_column("listings", "landmark_hi", new_column_name="landmark")
    op.drop_constraint("fk_listing_gate_photo", "listings", type_="foreignkey")
    op.drop_column("listings", "gate_photo_media_id")
    op.drop_column("listings", "location_accuracy_m")
