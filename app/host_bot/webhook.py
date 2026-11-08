import asyncio

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from telegram import Update

from app.config import get_settings
from app.db.models import TelegramUpdate
from app.db.session import session_factory

router = APIRouter()


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)
) -> dict[str, bool]:
    settings = get_settings()
    if (
        not settings.telegram_webhook_secret
        or x_telegram_bot_api_secret_token != settings.telegram_webhook_secret
    ):
        raise HTTPException(status_code=403, detail="invalid webhook secret")
    application = request.app.state.telegram_application
    if application is None:
        raise HTTPException(status_code=503, detail="telegram bot is not configured")
    payload = await request.json()
    update_id = payload.get("update_id")
    if not isinstance(update_id, int):
        raise HTTPException(status_code=400, detail="Telegram update_id is required")
    async with session_factory() as session:
        session.add(TelegramUpdate(update_id=update_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return {"ok": True}
    update = Update.de_json(payload, application.bot)
    asyncio.create_task(application.process_update(update))
    return {"ok": True}
