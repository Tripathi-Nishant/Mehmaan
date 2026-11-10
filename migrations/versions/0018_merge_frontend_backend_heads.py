"""Merge the landmark and dietary-notes migration heads."""

revision = "0018_merge_heads"
down_revision = ("0017_landmark_text", "0017_booking_dietary_notes")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
