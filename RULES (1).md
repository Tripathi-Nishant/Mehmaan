# RULES.md

These rules are mandatory. If a rule blocks you, stop and ask. Don't work around it.

## 0. How to work (agent workflow)

1. At session start, read CLAUDE.md, ARCHITECTURE.md, TECH_STACK.md and this file.
2. Work on **one build phase at a time**. Don't write code for later phases.
3. Before any multi-file change, state the plan in 3–6 bullets (files touched, what changes, how you'll test it), then do it.
4. Small diffs, one concern per commit.
5. If the spec is unclear, or two docs conflict, **stop and ask**. Quote the conflicting lines.
6. **Never claim done** without running `uv run pytest` and `uv run ruff check . && uv run ruff format --check .`. Report the exact commands and their results.
7. Never mark a task done if tests fail, anything is silently stubbed, or you skipped a DoD item. Stubs must raise `NotImplementedError("TODO(P<n>): ...")`.
8. **No new dependencies** without asking: give the name, why, and the alternative you considered.
9. Never edit an applied Alembic migration. Create a new one.
10. When you change a schema, state machine or flow, update ARCHITECTURE.md in the same commit.
11. New feature ideas go into `docs/V2.md` as one line. Don't build them.
12. **Phase review gate.** At the end of every phase, write `docs/reviews/P<n>.md` and **stop**. Don't start the next phase until Nancy approves. The review note contains:
    - what was built, mapped to the phase DoD
    - files changed, with **the 3–5 files to review first** and why
    - risky spots: concurrency, money, external calls, anything you're unsure about
    - manual test steps Nancy can run in under 10 minutes
    - commands run and their results (tests, ruff)
    - open questions and anything deferred to `docs/V2.md`

## 1. Correctness

- The code meets the current phase's DoD in CLAUDE.md.
- Edge cases and failure paths are handled (see ARCHITECTURE.md §7 and §5 below).
- Tests cover the important behavior (minimum list in §6).
- Unit tests make **no network calls**. Mock Gnani, LLM and Telegram with respx or fakes.

## 2. Design

- Each module has one clear purpose (layout in ARCHITECTURE.md §2).
- Dependencies are explicit: pass DB sessions and clients in as parameters. No module-level globals except `Settings`.
- Routes and handlers stay thin → service functions → DB.
- External calls live only in their module: Gnani in `app/gnani/`, LLM in `app/llm/`, payments in `app/payments/`, Telegram sends in `app/notifications/` and `app/host_bot/`.
- No more complex than needed. Don't add queues, caches, microservices, frameworks or abstraction layers that aren't in ARCHITECTURE.md.

## 3. Maintainability

- Intent-revealing names: `confirm_booking_by_host`, not `process` or `handle_data`.
- Small, cohesive functions (guideline: under ~40 lines).
- Type hints everywhere. Pydantic models at every boundary: HTTP, LLM output, external API responses.
- Domain exceptions (`SlotFullError`, `InvalidTransitionError`, `SttError`, `TtsError`, `LlmOutputError`, `PaymentVerificationError`). Messages say what failed and include the relevant id.
- Structured logs with `request_id`, `host_id`, `booking_id` where relevant. Log external-call latency.

## 4. Production readiness

- **No hardcoded secrets.** All config comes from `Settings` (pydantic-settings, `.env`). `.env` is gitignored; `.env.example` is committed.
- **Every external call has a timeout** (table in TECH_STACK.md §4).
- Retries only for idempotent calls, with exponential backoff and jitter, and the max retries from the table.
- DB changes only via Alembic migrations, each reversible (`downgrade` implemented).
- Concurrency: slot capacity uses `SELECT … FOR UPDATE`. Status changes use conditional updates. Idempotency uses unique constraints (`provider_payment_id`, `telegram_updates.update_id`).
- `ruff check`, `ruff format --check` and `pytest` all pass before anything is called done.

### Public exposure (the app runs on a public URL)
- Per-IP rate limits on search, booking and interpreter endpoints.
- Every Gnani call goes through the daily usage cap. Strangers must not be able to drain the programme credits.
- Booking and interpreter pages are reachable only via the random `access_token` (use `secrets.token_urlsafe(32)`). Never use sequential IDs in public URLs.
- The Telegram webhook rejects requests without the correct secret-token header, returns 200 fast, and processes updates in the background.
- No admin or debug pages exposed. FastAPI docs (`/docs`, `/openapi.json`) are disabled in prod. No CORS.
- Error pages never show stack traces, SQL or keys.

## 5. Domain rules (non-negotiable)

### Listings and AI
- A listing goes LIVE **only** after the host's explicit YES on the read-back.
- The read-back is rendered **from stored fields by a template**. The LLM never writes the read-back.
- All LLM output is validated with Pydantic → one retry with the validation error → then fall back (clarifying question, or SQL-only results).
- Search returns **only** listing IDs from the SQL candidate set. Drop anything else and log it.
- Never invent hosts, listings, reviews, ratings, badges or transcripts. Demo data goes through the real pipeline (`scripts/run_demo_voice_notes.py`).
- Demo hosts are role-played by the builder. They must have `is_demo_roleplay = true`, show "Demo host (role-play)" on every page where they appear, and be described as role-play in the demo video. Never present them as real hosts.
- LLM prompts live in `app/llm/prompts/` as files, never inline strings scattered in code.

### Money
- Integer **paise** only. No floats anywhere in money code.
- Amounts are computed server-side. Never trust an amount sent by the client.
- Verify the payment signature (constant-time compare) **before** marking anything paid, even though the provider is a mock.
- Every payment screen, booking page and host payment voice note says it's a TEST payment. Never imply real money moved.
- Every money movement writes ledger entries **in the same transaction** as the status change. The ledger is append-only.
- For every booking, `CHARGE = COMMISSION + HOST_PAYABLE`, and refunds/payouts never exceed what was charged. Assert this in tests.
- Payment verify and refund handlers are idempotent.

### Host safety
- No host-facing message ever asks for an OTP, PIN, card number, bank password or screenshot.
- Payment confirmations to hosts are sent only after a verified payment event.
- A UPI ID is read back to the host and verified (mocked penny-drop in the MVP) before it's saved.

### Traveler safety and privacy
- The exact address is shown only for CONFIRMED bookings, and only to that traveler.
- Phone numbers and UPI IDs are masked in logs and UI (`98******21`, `me***@okaxis`).
- A host's voice clip is public only if `consent_voice_clip = true`.
- Reviews only for COMPLETED bookings, one per booking per side.
- Transcripts are user content: log them at DEBUG only, never at INFO.

### Voice UX (host side)
- Simple Hindi, one question per message, short (aim for under 25 words per voice note).
- Always repeat numbers back: price, guests, dates, times.
- On STT failure or an empty transcript: "Awaaz saaf nahi aayi, kripya phir se bhejiye."
- If TTS fails, send the same message as text.
- Max 12 turns per onboarding session; then offer human help.

## 6. Minimum tests

- Onboarding state machine: field merge, missing-field order, CHANGE loops back, abandon after the turn limit.
- Read-back template: renders all fields, including the payout line, with correct ₹ formatting.
- Intent classification fallbacks: haan / nahi / unclear / LLM failure.
- LLM output validation: invalid JSON → retry → fallback.
- Search grounding: an ID not in the candidates is dropped.
- Booking: concurrent holds on the last seat (exactly one succeeds); hold expiry releases seats; invalid transition raises.
- Payments: valid and invalid signatures; duplicate verify is a no-op; ledger balances; refund ≤ charge.
- Cancellation policy math (free >48 h, 50% within 48 h, 100% no-show).
- Interpreter: speaker → correct STT language and target language; glossary terms preserved.
- Address visibility: hidden unless CONFIRMED.

## 7. Definition of done (every task)

- [ ] Meets the phase DoD and the task's stated requirement
- [ ] Failure paths handled and logged
- [ ] Tests added or updated; `uv run pytest` passes
- [ ] `ruff check` and `ruff format --check` pass
- [ ] No secrets, no PII in logs, timeouts on all new external calls
- [ ] Migration added if the schema changed (with downgrade)
- [ ] ARCHITECTURE.md updated if a schema, state or flow changed
- [ ] Summary posted: what changed, commands run with results, anything left open

## 8. Git

- Conventional commits: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`.
- Never commit `.env`, API keys, or **audio/photos of real people**. Keep `media/` and `demo_data/` in `.gitignore` unless the person has consented to publication.
