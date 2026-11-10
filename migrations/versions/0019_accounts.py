"""Add role-based accounts, sessions, and booking ownership."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019_accounts"
down_revision = "0018_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column(
            "traveler_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("travelers.id"), unique=True
        ),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hosts.id"), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_accounts_email", "user_accounts", ["email"], unique=False)
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_accounts.id"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=False)
    op.add_column(
        "bookings",
        sa.Column(
            "traveler_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_accounts.id")
        ),
    )


def downgrade() -> None:
    op.drop_column("bookings", "traveler_account_id")
    op.drop_index("ix_auth_sessions_token_hash", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_user_accounts_email", table_name="user_accounts")
    op.drop_table("user_accounts")
