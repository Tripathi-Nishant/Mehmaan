# TECH_STACK.md

## 1. Stack

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Fastest path |
| Package manager | `uv` | Fast installs, lockfile |
| Web framework | FastAPI | Async, typed, simple |
| Templates | Jinja2 + a little vanilla JS | No frontend build step; backend-first |
| DB | PostgreSQL 16 (docker compose locally; managed Postgres in prod) | Row locks, JSONB, arrays, bytea for media |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic | Explicit schema changes |
| DB driver | asyncpg | Async Postgres |
| Validation / config | Pydantic v2 + pydantic-settings | Every I/O boundary is typed |
| HTTP client | httpx (async) | Timeouts, easy to mock |
| Telegram | python-telegram-bot v21+ (async). Polling locally, webhook in prod | Same handlers in both modes |
| STT | **Gnani Prisma v2.5** (REST) | Required; Indian speech, code-mixed |
| TTS | **Gnani Timbre** (REST) | Required; Hindi voice notes |
| LLM | **Groq** via its OpenAI-compatible API, called with httpx. Swap to Evon via env if Gnani hosts it | Fast; provider set by env only |
| Payments | `MockProvider` behind a `PaymentProvider` interface | Gnani doesn't score payments; the verify and idempotency logic is still real |
| Audio | ffmpeg (system binary; installed in the Docker image) | OGG/WebM ↔ WAV ↔ OGG/Opus |
| Deploy | One Docker image on an always-on host + managed Postgres | Public URL for judges |
| Tests | pytest, pytest-asyncio, respx | Mock all external HTTP |
| Lint / format | ruff (lint + format) | One tool |

Versions: use latest stable at setup and pin via `uv.lock`. Do not upgrade mid-build.

**Not allowed for the MVP:** React/Next.js, Celery/Redis/Kafka, LangChain/LangGraph, LiveKit, pgvector, object storage/S3, Kubernetes, multiple instances, real payment providers.

## 2. Gnani API reference

> Taken from the Gnani quick start and `livekit-plugins-gnani` docs on 2026-11-06. **Verify every endpoint, field and audio format against docs.gnani.ai in P0 before coding against it.**

- **Base URL:** `https://api.vachana.ai`
- **Auth header:** `X-API-Key-ID: <GNANI_API_KEY>`

### Prisma STT (REST)
```
POST /stt/v3
Content-Type: multipart/form-data
fields: audio_file=<file>, language_code=hi-IN | en-IN | ...
→ {"success": true, "transcript": "..."}
```
- Streaming exists over WebSocket. Docs show both `wss://api.vachana.ai/stt/v3` and `wss://api.vachana.ai/stt/v3/stream`, so **verify** which is correct. MVP uses REST only.
- **Verify:** accepted audio formats (is OGG/Opus accepted, or WAV only?), max duration, sample rate, whether confidence is returned.

### Timbre TTS (REST)
```
POST /api/v1/tts/inference
Content-Type: application/json
{"text": "...", "voice": "<voice>", ...}
→ binary audio
```
- Also available: SSE at `POST /api/v1/tts/sse` and WebSocket at `wss://api.vachana.ai/api/v1/tts`.
- Models: `timbre-v2.0` (default) and `timbre-v2.5` (takes a `language` such as `hi-IN`, larger voice set).
- **Verify:** exact request fields for model/language, voice names for Hindi and English, output format (WAV/MP3/PCM) and sample rate.
- Voice cloning exists (`/api/v1/tts/voice-clone/embeddings`). **Not used in MVP.**

### Evon / Warp
- **Verify:** does Evon v3.3 have a hosted API (ideally OpenAI-compatible)? What is "Warp" in the model overview? If either is hosted and usable, switch the LLM env vars to it (stronger Gnani story).

## 3. Other external APIs

### Groq (LLM)
- Base URL: `https://api.groq.com/openai/v1` (OpenAI-compatible `/chat/completions`).
- Model: set `LLM_MODEL`. In P0, test 2–3 current Groq models on 5 real Hindi/Hinglish transcripts and pick the one with the best extraction accuracy. Record the choice here.
- Use JSON-mode / structured output where supported; always validate with Pydantic anyway.
- Temperature: 0 for extraction, intent and search; ≤ 0.3 for English listing copy and translation.

### Telegram
- Incoming voice notes are OGG/Opus → convert to 16 kHz mono WAV for Prisma (unless P0 shows OGG is accepted).
- Outgoing voice notes must be **OGG/Opus** to display as a voice note: `ffmpeg -i in.wav -c:a libopus -b:a 32k out.ogg`.
- Webhook mode: `setWebhook` with `secret_token`; verify the `X-Telegram-Bot-Api-Secret-Token` header. Telegram retries failed deliveries, so dedupe on `update_id`.
- Return 200 quickly from the webhook and process the update in a background task, so slow STT/LLM calls don't trigger Telegram retries.

### Mock payments
- `create_order` → `mock_order_<uuid>`. Pay → `payment_id` + `signature = HMAC-SHA256(order_id + "|" + payment_id, MOCK_PAYMENT_SECRET)`.
- Verification uses a constant-time compare (`hmac.compare_digest`). This is the same contract a real provider (Razorpay, v2) would satisfy.
- Foreign currency is **display only**: static approximate rates in config, labelled "approx."

## 4. Timeouts and retries

| Call | Timeout | Retries |
|---|---|---|
| Prisma STT (onboarding) | 30 s | 2, exponential backoff + jitter |
| Prisma STT (interpreter) | 10 s | 0 (latency-bound) |
| Timbre TTS (notifications) | 20 s | 2 |
| Timbre TTS (interpreter) | 10 s | 0 |
| Groq (onboarding/search) | 30 s | 1 (plus 1 validation retry) |
| Groq (interpreter) | 10 s | 0 |
| Telegram send | 20 s | 2 |
| ffmpeg subprocess | 20 s | 0 |

## 5. Environment variables (`.env`, never committed; commit `.env.example`)

```
DATABASE_URL=postgresql+asyncpg://mehmaan:mehmaan@localhost:5432/mehmaan
PUBLIC_BASE_URL=http://localhost:8000
GNANI_API_KEY=
GNANI_BASE_URL=https://api.vachana.ai
GNANI_TTS_MODEL=timbre-v2.5
GNANI_TTS_VOICE_HI=
GNANI_TTS_VOICE_EN=
GNANI_DAILY_CALL_CAP=800
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=
LLM_MODEL=
TELEGRAM_BOT_TOKEN=
BOT_MODE=polling                 # polling | webhook
TELEGRAM_WEBHOOK_SECRET=
PAYMENT_PROVIDER=mock
MOCK_PAYMENT_SECRET=
COMMISSION_BPS=1500              # 15.00%
HOLD_MINUTES=15
HOST_REPLY_TIMEOUT_MINUTES=720   # demo: 2
PAYOUT_DELAY_MINUTES=1440        # demo: 2
RATE_LIMIT_PER_MIN=20
LOG_LEVEL=INFO
```

## 6. Local setup and deploy

```bash
# prerequisites: uv, docker, ffmpeg
uv sync
cp .env.example .env              # fill keys
docker compose up -d db
uv run alembic upgrade head
uv run python scripts/smoke_gnani.py
uv run uvicorn app.main:app --reload   # website + bot (polling) + jobs
```

**Deploy (end of P2, then on every change):**
1. Build the Docker image (Python 3.12 slim + `apt-get install ffmpeg` + `uv sync --frozen`).
2. Create managed Postgres; set all env vars on the host, with `BOT_MODE=webhook` and `PUBLIC_BASE_URL=https://<your-domain>`.
3. Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Check `/healthz`, then send the bot a voice note.

`pyproject.toml` ruff config: line length 100, target py312, rules `E,F,I,B,UP,SIM,ASYNC`.

## 7. Open questions — answer in P0 and record the answers here

- [ ] Prisma accepted audio formats and max length
- [ ] Timbre request fields for model + language; Hindi and English voice names; output format
- [ ] Credits consumed per STT/TTS call (5,000 programme credits) → set `GNANI_DAILY_CALL_CAP`
- [ ] Evon hosted endpoint? Warp = what?
- [ ] Prisma quality on: soft speech, kitchen noise, heavy Hinglish, non-Indian English accent (all recorded by Nancy; elderly speech is untested, so say so in the pitch)
- [ ] Groq model choice for Hindi extraction (test on 5 transcripts)
- [ ] Hosting provider: confirm the plan is always-on (doesn't sleep), supports Docker, and has managed Postgres. Check current pricing before committing
