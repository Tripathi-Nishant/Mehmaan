# Architecture implementation status

The current service follows the supplied one-process architecture. Implemented modules include:

- FastAPI/Uvicorn service with Jinja website and Telegram webhook boundary.
- Host onboarding state machine, Prisma STT boundary, Groq extraction boundary, and PostgreSQL persistence models.
- LIVE-only browse/search, slots, access-token booking pages, mock checkout, HMAC payment verification, booking transitions, and ledger math.
- Gnani usage guard, media size guard, per-key rate limiter, scheduler lifecycle hook, and interpreter upload boundary.

Remaining validation is external-state work: run the migration chain against managed PostgreSQL, register the Telegram webhook, and exercise real Prisma/Timbre/Groq calls with configured credentials. The code-side webhook dispatch, host voice notification adapter, background DB jobs, and glossary-preserving translation prompt are implemented.

The complete migration chain was also verified in Alembic offline mode through `0008_booking_deadlines`; it generated 147 SQL lines successfully.
