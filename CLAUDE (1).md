# CLAUDE.md — Mehmaan

> "Mehmaan" is a working name. Rename freely.
> Entry for Gnani AI's **Great Indian AI Internship Challenge**.

## What this is

A voice-first marketplace for authentic local experiences in India.

- **Hosts** (elderly home cooks, artisans, folk musicians) can't type or write English. They list experiences **by speaking Hindi/Hinglish on Telegram**. The system writes the listing and publishes it on the website.
- **Travelers** browse and book on the **website** (English).
- Hosts get booking alerts, payment confirmations and payout notices as **Hindi voice notes**.
- During the experience, a push-to-talk **interpreter page** lets host and traveler talk (Hindi ↔ English).

## Hard constraints

- **Deadline:** final submission closes **11:59 PM IST, Nov 10, 2026**. Target: done by Nov 10 evening.
- **Must use Gnani models:** Prisma (STT) and Timbre (TTS). Evon (LLM) only if a hosted endpoint exists. Every Gnani call goes through `app/gnani/`.
- **No misleading demos.** Every listing, booking and voice note in the demo must come from a real run of the pipeline. Never hardcode outputs to look like pipeline results.
- **Scope is locked.** Build only the phases below. Any new idea → one line in `docs/V2.md`. Do not build it.

## Locked decisions

- **Solo build** (Nancy). The README states it's a solo build and that all components were built by her.
- **Gnani challenge only.** No PayPal integration and no PayPal provider code.
- **Languages:** host side Hindi + Hinglish (`hi-IN`); traveler side English (`en-IN`). No other Indian languages in the MVP.
- **Award targets:** Real Deal (primary), Mixed Vibes (Hinglish), Solo Ninja.
- **Demo hosts are role-played by Nancy.** Every demo host is created through the real pipeline, flagged `is_demo_roleplay = true`, shown as "Demo host (role-play)" on the website, and described as role-play in the demo video.
- **LLM:** Groq via its OpenAI-compatible API. Swap to Evon only through env vars, if Gnani hosts it.
- **Payments: mock only.** `MockProvider` behind the `PaymentProvider` interface, with real signature verification, idempotency and ledger. Every payment screen says "TEST PAYMENT — no real money".
- **Public URL.** One always-on service, single instance, managed Postgres. Telegram uses webhook mode in prod and polling locally.
- **Working mode: the agent writes, Nancy reviews.** At the end of every phase the agent writes `docs/reviews/P<n>.md` and **stops** until Nancy approves.

## Read before coding (every session)

1. `ARCHITECTURE.md`: components, data model, state machines, flows
2. `TECH_STACK.md`: libraries, Gnani API reference, env vars, setup
3. `RULES.md`: coding rules and definition of done (**mandatory**)

If these documents conflict, stop and ask. Don't guess.

## Surfaces

| Who | Where | Language |
|---|---|---|
| Host | Telegram bot (webhook in prod, polling locally) | Hindi / Hinglish voice |
| Traveler | Website (FastAPI + Jinja templates) | English |
| Host + traveler, during the experience | Interpreter page on the website | Hindi ↔ English |

## Build phases

Work in order. A phase is finished when its DoD passes **and** Nancy has approved `docs/reviews/P<n>.md`. Don't start the next phase before both.

### P0 — Setup (Nov 6, tonight)
- Repo, `uv`, ruff, pytest, Postgres via docker compose, settings, Alembic.
- `scripts/smoke_gnani.py`: transcribe a sample Hindi voice note with Prisma; synthesize a Hindi sentence with Timbre.
- **DoD:** the smoke script prints a Hindi transcript and writes a playable audio file. All open questions in TECH_STACK.md §7 are answered and recorded there.

### P1 — Host onboarding bot (Nov 7)
- Telegram voice note → Prisma → LLM extraction → one follow-up question at a time, voiced by Timbre → template read-back → host says "haan" → listing `LIVE`.
- Photos sent by the host are attached to the draft listing.
- **DoD:** a real Hindi voice note produces a `LIVE` listing in the DB. Tests pass for the onboarding state machine, extraction validation, the read-back template and intent classification fallbacks.

### P2 — Website: listings and search (Nov 8, morning)
- Browse page, listing page (English copy, host voice clip if consented, area only, badges, price in INR plus an approximate figure in foreign currency), natural-language search box.
- Deploy the skeleton to the public URL (Dockerfile, managed Postgres, `BOT_MODE=webhook`), so deployment problems surface early.
- **DoD:** only `LIVE` listings render. Search returns only real listing IDs (tested). The exact address never appears on the listing page. The public URL serves the site, and the bot answers a voice note in webhook mode.

### P3 — Booking, payments, host confirmation (Nov 8, evening)
- Pick a slot → `HELD` → mock checkout page (TEST) → signature verified → `PAID_PENDING_HOST` → Timbre voice note to host → "haan" → `CONFIRMED` → address revealed on the traveler's booking page `/b/{access_token}`. "nahi" or timeout → `DECLINED` → `REFUNDED`.
- **DoD:** end-to-end flow works. Tests cover concurrent booking of the last seat, payment idempotency, invalid transitions and ledger balance.

### P4 — Interpreter (Nov 9, morning)
- Two push-to-talk buttons (host Hindi / traveler English). Each turn runs record → Prisma → LLM translate (glossary-aware) → Timbre → play, with both languages shown on screen.
- **DoD:** both directions work. Typical round trip ≤ 4 s, measured and logged.

### P5 — Polish and demo (Nov 9, evening)
- Mock payout plus a voice note to the host. The host can ask "Mera paisa kab aayega?" by voice. Reviews only for completed bookings. Verification and hygiene badges.
- Record 3–5 role-play host voice notes (different personas and experiences; at least one heavy Hinglish, one with kitchen noise such as a pressure cooker or fan, one spoken softly) and run them through the real pipeline. Record the 60 s demo.
- **DoD:** the demo script below runs end to end **on the public URL** without manual DB edits.

### P6 — Submit (Nov 10)
- Post the demo on LinkedIn/X with #GnaniAI and #GreatIndianAIInternshipChallenge **before** submitting. The README names the Gnani models used and states it's a solo build. Submit by evening.

## Commands

```bash
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload        # website + bot (BOT_MODE=polling) + background jobs
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run python scripts/smoke_gnani.py
```

## Key design decisions (don't change without asking)

- The **read-back** to the host is rendered from stored fields by a **template**, never written by the LLM. What she confirms is exactly what's stored.
- **Grounded search:** SQL filters produce candidates, the LLM ranks only those IDs, and the IDs are validated.
- **Money:** integer paise only, computed server-side.
- **Slot booking** uses a row lock (`SELECT … FOR UPDATE`). Status changes are conditional updates.
- The **exact address** is hidden until the booking is `CONFIRMED`.
- **One process, one instance:** website, Telegram bot, interpreter API and job loop all run in `app.main`. Never run two instances.
- **Payments sit behind a `PaymentProvider` interface.** Only `MockProvider` exists; Razorpay is v2.
- **Media (audio, photos) is stored in Postgres**, because the host's disk is ephemeral.
- **Travelers have no accounts.** Bookings and the interpreter are reachable only via a random `access_token` link.
- **Public endpoints are rate-limited**, and Gnani calls are capped per day (`GNANI_DAILY_CALL_CAP`) to protect credits.

## Demo script (60 s)

1. A role-play host sends a Hindi/Hinglish voice note on Telegram (on-screen label: "role-play host").
2. The bot asks one follow-up in Hindi voice; she answers.
3. Read-back plays; she says "haan"; the listing appears on the website in English.
4. A traveler searches "food + crafts, Saturday", books, and pays in test mode.
5. The host receives a Hindi voice note and confirms by voice.
6. 10 s of interpreter: Hindi ↔ English.

## Glossary

| Term | Meaning |
|---|---|
| haan / nahi | yes / no |
| mehmaan | guest |
| read-back | system reads the full listing aloud to the host before publishing |
| host prompt | an open question the bot is waiting for the host to answer (see ARCHITECTURE.md) |
| paise | 1/100 rupee; all money is stored in paise |
