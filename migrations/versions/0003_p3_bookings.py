"""add traveler booking and payment records

Revision ID: 0003_p3_bookings
Revises: 0002_p3_slots
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_p3_bookings"
down_revision = "0002_p3_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, columns in {
        "travelers": [
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        ],
        "bookings": [
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("access_token", sa.String(64), unique=True, nullable=False),
            sa.Column(
                "slot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("slots.id"), nullable=False
            ),
            sa.Column(
                "traveler_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("travelers.id"),
                nullable=False,
            ),
            sa.Column("guests", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("amount_paise", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        ],
        "payments": [
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "booking_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("bookings.id"),
                unique=True,
                nullable=False,
            ),
            sa.Column("provider_order_id", sa.String(120), unique=True, nullable=False),
            sa.Column("provider_payment_id", sa.String(120), unique=True),
            sa.Column("amount_paise", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        ],
    }.items():
        op.create_table(table, *columns)


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("bookings")
    op.drop_table("travelers")
