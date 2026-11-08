"""add host onboarding tables

Revision ID: 0001_p1_onboarding
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_p1_onboarding"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hosts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(120)),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("city", sa.String(120)),
        sa.Column("area", sa.String(120)),
        sa.Column("consent_voice_clip", sa.Boolean(), nullable=False),
        sa.Column("is_demo_roleplay", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "onboarding_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hosts.id"), unique=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("fields", postgresql.JSONB(), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hosts.id"), nullable=False
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("title_en", sa.String(200)),
        sa.Column("description_hi", sa.Text()),
        sa.Column("source_transcript", sa.Text()),
        sa.Column("price_per_person_paise", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("area", sa.String(120), nullable=False),
        sa.Column("exact_address", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("listings")
    op.drop_table("onboarding_sessions")
    op.drop_table("hosts")
