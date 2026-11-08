# ARCHITECTURE.md

## 1. System overview

```
HOST (Telegram)                              ONE SERVICE (single instance)                       TRAVELER (Browser)
voice notes, photos ──► Telegram ──webhook──►  FastAPI app                                   ◄──  website (Jinja pages)
                       (polling locally)       ├─ host bot (python-telegram-bot)
                                               ├─ website + booking + mock payments
                                               ├─ interpreter API
                                               └─ background job loop
                                                        │
                              app/gnani (Prisma, Timbre) · app/llm (Groq) · Postgres (data + media)
```

- **One process, one instance.** `uvicorn app.main:app` runs the website, the Telegram bot, the interpreter API and the background job loop. The lifespan starts the bot (`BOT_MODE=polling` locally, `webhook` when deployed) and the job loop.
- **Exactly one instance in production.** The rate limiter and job loop assume a single instance. Don't scale horizontally.
- **Deployed to a public HTTPS URL** on an always-on host with managed Postgres (see §9).

## 2. Directory layout

```
app/
  main.py               # FastAPI app; lifespan starts bot + job loop
  config.py             # pydantic-settings Settings
  db/
    models.py           # SQLAlchemy 2.0 models
    session.py          # async engine + session factory
  media/store.py        # save/load audio & photos as Postgres blobs (host disks are ephemeral)
  gnani/
    stt.py              # Prisma: transcribe(wav_bytes, language) -> SttResult
    tts.py              # Timbre: synthesize(text, language, voice) -> bytes
    usage.py            # daily call counter + cap (protects programme credits)
  audio/convert.py      # ffmpeg: ogg/webm -> 16k mono wav; wav/mp3 -> ogg/opus
  llm/
    client.py           # OpenAI-compatible chat client (Groq; Evon later via env)
    prompts/            # one file per prompt
    schemas.py          # Pydantic models for every LLM output
  host_bot/
    app.py              # builds the PTB Application, registers handlers
    webhook.py          # POST /telegram/webhook (secret-token checked)
    handlers.py         # voice, photo, text handlers
    router.py           # route a host message to an open host_prompt or a new intent
    onboarding.py       # onboarding state machine
    readback.py         # Hindi read-back template rendering
    intents.py          # YES / NO / CHANGE / PAYOUT_QUERY / NEW_LISTING / UNCLEAR
  listings/service.py   # create/update/publish listings, slot generation
  search/service.py     # SQL candidates -> LLM rank -> validate IDs
  booking/
    service.py          # hold, confirm, decline, complete
    states.py           # allowed transitions + transition()
    policy.py           # cancellation/refund math
  payments/
    provider.py         # PaymentProvider protocol (Razorpay adapter is v2)
    mock_provider.py    # TEST provider: orders, signed results, refunds
    service.py          # create order, verify, refund
    ledger.py           # append-only ledger writes + balance checks
  notifications/host_voice.py   # text -> Timbre -> ogg -> Telegram send_voice
  interpreter/
    routes.py           # POST /interpreter/{access_token}/turn
    service.py          # STT -> translate -> TTS, latency logging
  jobs/scheduler.py     # periodic asyncio loop
  web/
    routes.py
    ratelimit.py        # in-memory per-IP token bucket (single instance)
    templates/
    static/             # minimal JS: MediaRecorder for interpreter
migrations/             # Alembic
scripts/
  smoke_gnani.py
  run_demo_voice_notes.py   # feeds recorded role-play voice notes through the REAL pipeline
tests/
docs/
  V2.md
  reviews/P<n>.md       # phase review notes for Nancy
Dockerfile
docker-compose.yml      # local Postgres only
```

## 3. Data model

All timestamps are stored in UTC and displayed in Asia/Kolkata. All money is in **integer paise**.

| Table | Key columns | Notes |
|---|---|---|
| `hosts` | id, telegram_user_id (unique), telegram_chat_id, display_name, phone (nullable), language (default `hi-IN`), city, area, upi_id (nullable), upi_verified, verification_tier (0–3), consent_voice_clip, is_demo_roleplay, created_at | Phone and UPI never logged unmasked. Role-play hosts labelled "Demo host (role-play)" everywhere |
| `onboarding_sessions` | id, host_id, state, fields (JSONB), turn_count, listing_id (nullable), updated_at | One open session per host |
| `listings` | id, host_id, status, category, title_en, description_en, description_hi, duration_min, max_guests, price_per_person_paise, city, area, exact_address, start_time_local, available_weekdays (int[]), food_type, languages, hygiene_badge, voice_clip_media_id, source_transcript, created_at, published_at | `exact_address` only rendered for CONFIRMED bookings |
| `listing_photos` | id, listing_id, media_id, created_at | |
| `media` | id, kind (audio/photo), content_type, data (bytea), size_bytes, created_at | Max 5 MB per item. Served via `/media/{id}` only when the owner listing is LIVE and consent allows |
| `slots` | id, listing_id, starts_at, capacity, booked_count | Unique (listing_id, starts_at). Generated for the next 30 days on publish |
| `travelers` | id, name, email, phone, country, created_at | No accounts or passwords |
| `bookings` | id, access_token (unique, random), slot_id, traveler_id, guests, status, amount_paise, commission_paise, host_payout_paise, hold_expires_at, host_reply_deadline, checked_in_at, checked_out_at, created_at, confirmed_at | The traveler reaches the booking only via `/b/{access_token}` |
| `payments` | id, booking_id, provider (`mock`), provider_order_id (unique), provider_payment_id (unique, nullable), amount_paise, status, created_at | Unique constraints enforce idempotency |
| `ledger_entries` | id, booking_id, host_id (nullable), type, amount_paise (signed), created_at | **Append-only**. Types: CHARGE, COMMISSION, HOST_PAYABLE, PAYOUT, REFUND |
| `payouts` | id, host_id, booking_id, amount_paise, status, scheduled_for, sent_at | Status goes to SENT_MOCK, never a real transfer |
| `reviews` | id, booking_id, author_role, hygiene, safety, accuracy, warmth (1–5), text, text_translated, created_at, visible_at | Only for COMPLETED bookings |
| `host_prompts` | id, host_id, kind, ref_id, status, expires_at, created_at | What the bot is waiting for the host to answer |
| `voice_turns` | id, host_id, booking_id, direction (IN/OUT), purpose, audio_media_id, text, language, latency_ms, extracted (JSONB), created_at | Debug log and eval dataset |
| `telegram_updates` | update_id (PK), received_at | Dedupe of Telegram updates (webhooks retry) |
| `gnani_usage` | day, kind (stt/tts), count | Enforces `GNANI_DAILY_CALL_CAP` |

## 4. State machines

P1 implements the onboarding state machine in `app/host_bot/onboarding.py` and validates
incoming extraction updates with `ListingFieldsUpdate` before merging them into the session.
The persisted P1 schema is represented by `Host`, `OnboardingSessionRecord`, and `Listing`
in `app/db/models.py` and migration `0001_p1_onboarding`.

All status changes go through a single `transition()` per entity. It checks an allowed-transitions map and performs a conditional update (`UPDATE … SET status=:to WHERE id=:id AND status=:from`). A rowcount of 0 raises `InvalidTransitionError`.

### Onboarding session
```
COLLECTING ──(all required fields valid)──► READBACK ──(YES)──► DONE (listing LIVE)
     ▲                                          │
     └──────────────(CHANGE <field>)────────────┘
any ──(48h idle or 12 turns)──► ABANDONED
```

### Listing
```
DRAFT ──(host YES on read-back)──► LIVE ◄──► PAUSED (report / host request)
```

### Booking
```
HELD ──(payment verified)──► PAID_PENDING_HOST ──(host YES)──► CONFIRMED ──(check-out or end+2h)──► COMPLETED
  │                                │                                                                   │
  └─(15 min, unpaid)─► EXPIRED     └─(host NO or reply timeout)─► DECLINED ──► REFUNDED           (completion + payout delay)
                                                                                                       ▼
                                                                                           PAYOUT_SCHEDULED ──► PAID_OUT (mock)
```
Releasing seats: EXPIRED and DECLINED decrement `slots.booked_count` in the same transaction.

### Payment
```
CREATED ──(signature verified)──► CAPTURED ──► REFUNDED
   └──(TEST fail button / error)──► FAILED
```

## 5. Core flows

### 5.1 Host onboarding (P1)
1. An update arrives (webhook or polling). Dedupe on `update_id`. Download the OGG and convert it to 16 kHz mono WAV.
2. `router` checks for an OPEN `host_prompt`. If there is none and no open onboarding session, classify the intent (NEW_LISTING / PAYOUT_QUERY / HELP).
3. Check the Gnani usage cap, then `gnani.stt.transcribe(wav, "hi-IN")`. If it fails or the transcript is empty, send "Awaaz saaf nahi aayi, kripya phir se bhejiye."
4. LLM extraction → `ListingFieldsUpdate` (Pydantic). Merge into `onboarding_sessions.fields`. On invalid JSON, retry once with the validation error; if it still fails, ask a clarifying question.
5. Compute missing required fields. Ask **one** question for the highest-priority missing field (Hindi text → Timbre → OGG → `send_voice`). Create a `host_prompt(kind=ONBOARDING_FIELD)`.
6. When all required fields are valid → state READBACK. Render the read-back **from fields via template**, including the payout line ("Guest ₹1500 dega, aapko ₹1275 milenge"). Send it as voice plus text.
7. Host reply → intent: YES → create the listing, generate English copy (LLM), generate slots, status LIVE, confirm by voice. CHANGE → identify the field → back to COLLECTING. UNCLEAR → ask again (max 2), then offer help.

**Required fields:** category, activity description, duration, max guests, price per person, city, area, available weekdays, start time. Plus `food_type` when category = food.

### 5.2 Search (P2)
1. Parse the query into filters (LLM → `SearchFilters`). Fall back to keyword match if parsing fails.
2. SQL: LIVE listings matching city/date/category/food_type, with available slot capacity → candidate set (max 20).
3. LLM ranks the candidates and writes a one-line reason. **Drop any returned ID not in the candidate set.** If the LLM fails, return the SQL order.

### 5.3 Booking and mock payment (P3)
1. `create_hold(slot_id, guests, traveler)`: lock the slot row with `FOR UPDATE`, check capacity, increment `booked_count`, create a HELD booking with a random `access_token` and `hold_expires_at = now + 15 min`. Amounts are computed server-side.
2. `payments.create_order(booking)` → `MockProvider` returns `mock_order_<uuid>` → redirect to `/pay/mock/{order_id}`. This page is clearly labelled **"TEST PAYMENT — no real money"** and has Pay and Fail buttons.
3. Pay → the mock provider generates `payment_id` and `signature = HMAC-SHA256(order_id|payment_id, MOCK_PAYMENT_SECRET)` → `POST /payments/verify`. This is the **same verify code path a real provider would use**: constant-time signature check → in one transaction: payment CAPTURED, ledger CHARGE + COMMISSION + HOST_PAYABLE, booking → PAID_PENDING_HOST, `host_reply_deadline` set. Idempotent on `provider_payment_id`.
4. `notifications.host_voice.send_booking_request()` → `host_prompt(kind=BOOKING_CONFIRM, ref_id=booking_id)`.
5. Host YES → CONFIRMED → the booking page `/b/{access_token}` now shows the exact address. NO or timeout → DECLINED → mock refund → ledger REFUND → REFUNDED → the booking page shows the refund.

### 5.4 Interpreter turn (P4)
`POST /interpreter/{access_token}/turn` with `speaker` (host|traveler) and audio (webm/opus from MediaRecorder).
1. Check the booking is CONFIRMED and within ±12 h of the slot. Apply the rate limit and the Gnani usage cap.
2. Convert to WAV → Prisma (`hi-IN` for host, `en-IN` for traveler).
3. LLM translate with listing context and a glossary (dish and craft names stay untranslated; numbers kept exact).
4. Timbre in the target language → return JSON `{source_text, translated_text, audio_b64, latency_ms}`.
5. Log per-stage latency in `voice_turns`. Target ≤ 4 s total for a typical turn.

### 5.5 Payout and "Mera paisa kab aayega?" (P5)
- Job: COMPLETED + payout delay → create a payout (SCHEDULED) → PAYOUT_SCHEDULED → mock send → SENT_MOCK, ledger PAYOUT → PAID_OUT → host voice note "₹X aapke UPI mein bhej diye (test)".
- PAYOUT_QUERY intent → answer from the ledger and payouts tables (template, not LLM): amount pending, expected date.

## 6. Background jobs (`app/jobs/scheduler.py`)

An asyncio loop in the app lifespan runs every 30 s on the single instance. Each job is a conditional update, so it is safe to run twice.

| Job | Condition | Action |
|---|---|---|
| expire_holds | HELD and `hold_expires_at < now` | → EXPIRED, release seats |
| host_reply_timeout | PAID_PENDING_HOST and `host_reply_deadline < now` | → DECLINED → refund |
| complete_bookings | CONFIRMED and slot end + 2 h < now | → COMPLETED |
| schedule_payouts | COMPLETED and completion + payout delay < now | create payout, → PAYOUT_SCHEDULED |
| send_mock_payouts | payout SCHEDULED and due | → SENT_MOCK, ledger, voice note |
| expire_prompts | OPEN `host_prompt` past `expires_at` | → EXPIRED |

Delays are configurable. Demo values are short (minutes); defaults are realistic (hours).

## 7. Failure handling

| Failure | Behavior |
|---|---|
| Prisma error / timeout / empty transcript | Host gets the "phir se bhejiye" voice/text message. Logged with host_id |
| Timbre error | Send the same message as Telegram **text** instead of voice |
| Gnani daily cap reached | Host: text message "Thodi der baad koshish kariye". Web: 503 with a friendly page. Logged as a warning |
| LLM invalid output | Retry once with the validation error → then a clarifying question (host) or SQL-only results (search) |
| LLM unavailable | Onboarding pauses with an apology message; search falls back to SQL order; interpreter shows the transcript without translation |
| Payment signature invalid | 400, booking stays HELD, logged as a warning |
| Duplicate payment verify | No-op returning the existing state (unique `provider_payment_id`) |
| Slot full at hold time | `SlotFullError` → 409 → UI shows other slots |
| Telegram send failure | Retry twice with backoff; if still failing, keep the prompt OPEN and log an error |
| Webhook with a wrong secret token | 403, nothing processed |

## 8. Trust and safety in the MVP

- Listing goes LIVE only after the host's explicit YES on a template read-back.
- Exact address shown only on `/b/{access_token}` after CONFIRMED. Phone and UPI masked everywhere.
- A host's voice clip is public only if `consent_voice_clip = true`.
- Reviews only from COMPLETED bookings.
- Badges render from `verification_tier` and `hygiene_badge`. Demo hosts are role-played by the builder, created through the real pipeline, and flagged `is_demo_roleplay`. Their listing pages show "Demo host (role-play)", and their badges are marked "demo".
- The bot never asks for OTP, PIN, card numbers or passwords. Payment confirmations to hosts come only from verified-payment events. Every payment screen says TEST.

## 9. Deployment (public URL)

- **One Docker image:** Python 3.12 slim + ffmpeg + uv. The start command runs `alembic upgrade head`, then `uvicorn app.main:app` (safe because there is one instance).
- **Host:** an always-on web service (a plan that does **not** sleep; otherwise the bot goes silent) plus managed Postgres. HTTPS required.
- **Telegram:** `BOT_MODE=webhook`. On startup, call `setWebhook(PUBLIC_BASE_URL/telegram/webhook, secret_token=TELEGRAM_WEBHOOK_SECRET)`. Reject any request whose `X-Telegram-Bot-Api-Secret-Token` header doesn't match.
- **Media in Postgres**, because container disks are ephemeral.
- **Public-exposure protections:**
  - per-IP rate limits on search, booking and interpreter endpoints
  - `GNANI_DAILY_CALL_CAP`, so strangers can't drain the programme credits
  - booking and interpreter pages reachable only via the random `access_token`
  - no admin pages exposed; debug mode off; no CORS
- `/healthz` returns DB connectivity status.
- Deploy the skeleton early (end of P2) so deployment problems surface before demo day.

## 10. Out of scope (v2, pitch only)

WhatsApp channel, Razorpay/real payments, real UPI payouts and host KYC, in-person verifier workflow, SOS and live location, email notifications, fake-review detection, disputes UI, live two-way call interpreter, pgvector semantic search, bundles, pricing assistant, voice calendar, multi-language listings beyond English, horizontal scaling.
