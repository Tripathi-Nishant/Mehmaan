"""Allow full host-provided landmark text."""

from alembic import op

revision = "0017_landmark_text"
down_revision = "0016_email_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE listings ALTER COLUMN landmark_hi TYPE TEXT")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE listings ALTER COLUMN landmark_hi TYPE VARCHAR(200)"
    )
