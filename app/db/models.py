import secrets
from datetime import datetime, time
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Host(Base):
    __tablename__ = "hosts"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    # Telegram ids exceed 32 bits; the DB columns are BIGINT.
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger)
    display_name: Mapped[str | None] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(10), default="hi-IN")
    city: Mapped[str | None] = mapped_column(String(120))
    area: Mapped[str | None] = mapped_column(String(120))
    consent_voice_clip: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo_roleplay: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OnboardingSessionRecord(Base):
    __tablename__ = "onboarding_sessions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    host_id: Mapped[UUID] = mapped_column(ForeignKey("hosts.id"), unique=True)
    state: Mapped[str] = mapped_column(String(20), default="COLLECTING")
    fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    host_id: Mapped[UUID] = mapped_column(ForeignKey("hosts.id"))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    category: Mapped[str] = mapped_column(String(40))
    title_en: Mapped[str | None] = mapped_column(String(200))
    description_en: Mapped[str | None] = mapped_column(Text)
    description_hi: Mapped[str | None] = mapped_column(Text)
    source_transcript: Mapped[str | None] = mapped_column(Text)
    price_per_person_paise: Mapped[int]
    city: Mapped[str] = mapped_column(String(120))
    area: Mapped[str] = mapped_column(String(120))
    location_lat: Mapped[float | None]
    location_lng: Mapped[float | None]
    location_accuracy_m: Mapped[float | None]
    landmark_hi: Mapped[str | None] = mapped_column(Text)
    landmark_en: Mapped[str | None] = mapped_column(String(200))
    # Private: shown to the guest only after confirmation, never served by /media.
    gate_photo_media_id: Mapped[UUID | None] = mapped_column(ForeignKey("media.id"))
    duration_min: Mapped[int | None]
    max_guests: Mapped[int | None]
    available_weekdays: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))  # Mon=0
    start_time_local: Mapped[time | None] = mapped_column(Time)  # Asia/Kolkata wall clock
    food_type: Mapped[str | None] = mapped_column(String(20))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (UniqueConstraint("listing_id", "starts_at"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # UTC
    capacity: Mapped[int]
    booked_count: Mapped[int] = mapped_column(Integer, default=0)


class Traveler(Base):
    __tablename__ = "travelers"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    access_token: Mapped[str] = mapped_column(
        String(64), unique=True, default=lambda: secrets.token_urlsafe(32)
    )
    slot_id: Mapped[UUID] = mapped_column(ForeignKey("slots.id"))
    traveler_id: Mapped[UUID] = mapped_column(ForeignKey("travelers.id"))
    guests: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="HELD")
    amount_paise: Mapped[int] = mapped_column(Integer)
    commission_paise: Mapped[int] = mapped_column(Integer, default=0)
    host_payout_paise: Mapped[int] = mapped_column(Integer, default=0)
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    host_reply_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dietary_notes: Mapped[str | None] = mapped_column(String(200))  # guest's words, to the host
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), unique=True)
    provider_order_id: Mapped[str] = mapped_column(String(120), unique=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="CREATED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index(
            "uq_ledger_one_refund_per_booking",
            "booking_id",
            unique=True,
            postgresql_where=text("type = 'REFUND'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"))
    host_id: Mapped[UUID | None] = mapped_column(ForeignKey("hosts.id"))
    type: Mapped[str] = mapped_column(String(30))
    amount_paise: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailOutbox(Base):
    """Traveler emails, written in the same transaction as the status change they announce."""

    __tablename__ = "email_outbox"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"))
    kind: Mapped[str] = mapped_column(String(40))
    to_email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(String(120), unique=True)  # "{booking_id}:{kind}"
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/SENT/FAILED
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Payout(Base):
    __tablename__ = "payouts"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    host_id: Mapped[UUID] = mapped_column(ForeignKey("hosts.id"))
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), unique=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED")
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TelegramUpdate(Base):
    __tablename__ = "telegram_updates"
    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), unique=True)
    author_role: Mapped[str] = mapped_column(String(20), default="traveler")
    warmth: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
