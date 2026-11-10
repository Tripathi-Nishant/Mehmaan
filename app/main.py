import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.db.session import engine
from app.host_bot.app import build_application
from app.host_bot.webhook import router as telegram_router
from app.interpreter.routes import router as interpreter_router
from app.jobs.scheduler import scheduler_loop
from app.web.booking_routes import router as booking_router
from app.web.errors import http_error, server_error, validation_error
from app.web.guards import PublicRateLimitMiddleware
from app.web.media_routes import router as media_router
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    telegram_application = None
    if settings.telegram_bot_token:
        telegram_application = build_application(settings)
        await telegram_application.initialize()
        if settings.bot_mode == "webhook":
            await telegram_application.bot.set_webhook(
                f"{settings.public_base_url}/telegram/webhook",
                secret_token=settings.telegram_webhook_secret,
            )
        await telegram_application.start()
        if settings.bot_mode == "polling" and telegram_application.updater:
            await telegram_application.updater.start_polling()
    app.state.telegram_application = telegram_application
    scheduler = asyncio.create_task(scheduler_loop())
    yield
    scheduler.cancel()
    await asyncio.gather(scheduler, return_exceptions=True)
    if telegram_application:
        if settings.bot_mode == "polling" and telegram_application.updater:
            await telegram_application.updater.stop()
        await telegram_application.stop()
        await telegram_application.shutdown()
    await engine.dispose()


app = FastAPI(title="Mehmaan", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(PublicRateLimitMiddleware)
app.add_exception_handler(StarletteHTTPException, http_error)
app.add_exception_handler(RequestValidationError, validation_error)
app.add_exception_handler(Exception, server_error)
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
app.include_router(telegram_router)
app.include_router(web_router)
app.include_router(booking_router)
app.include_router(interpreter_router)
app.include_router(media_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return {"status": "degraded"}
    return {"status": "ok"}
