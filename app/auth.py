import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuthSession, UserAccount

SESSION_COOKIE = "mehmaan_session"
SESSION_DAYS = 14


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256$240000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


async def current_user(request: Request, session: AsyncSession) -> UserAccount | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    auth = await session.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_hash, AuthSession.expires_at > datetime.now(UTC)
        )
    )
    return await session.get(UserAccount, auth.user_id) if auth else None


async def create_session(db: AsyncSession, user: UserAccount) -> str:
    token = secrets.token_urlsafe(48)
    db.add(
        AuthSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
        )
    )
    await db.commit()
    return token


async def delete_session(db: AsyncSession, token: str | None) -> None:
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        auth = await db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
        if auth:
            await db.delete(auth)
            await db.commit()
