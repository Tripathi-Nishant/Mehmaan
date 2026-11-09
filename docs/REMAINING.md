# Remaining work (revised, Nov 9)

Spec-driven task list. Each task: spec → test first → minimal code → `uv run pytest` + `uv run ruff check .` → review.
Deadline: submit Nov 10 evening. **Must** tasks first, in order. **Cut** tasks go to `docs/V2.md`.

Done: **T1** media store · **T2** `.env.example` · **T3** bool fields · **T4** extraction prompt (cancellation_rule removed; fixed policy in read-back) · **T4b** location pin (migration 0012) · **T5** spoken haan/nahi + consent · **T6** CHANGE flow · **T7** one listing per host. (Phase B complete.) · **T8** full listing (migration 0013) · **T9** slot generation · **T10** English copy (migration 0014) · **T11** all upcoming slots (`POST /book` now takes `slot_id` as a form field). (Phase C complete.) · **T12** `/verify` guard · **T14** one hold implementation (fixed `/book` crash: Payment had `booking_id=None`) · **T13** Fail button · **T15** host booking replies (no table; text + voice; real-Postgres tests via `tests/conftest.py`) · **T16** location reveal on confirmation · **T17** traveler cancel (migration 0015: one REFUND row per booking; also fixed decline's unbalanced ledger; late-cancel host share is paid out) · **T19** email outbox + SMTP (migration 0016; decline/timeout also emails BOOKING_CANCELLED; empty `SMTP_HOST` = queue only).

## Phase A — Make the app start
**T2. `.env.example`** *(must)*
- Spec: every `Settings` field with a safe placeholder value.
- Accept: a test asserts the keys equal `Settings.model_fields`.

## Phase B — Onboarding can finish
**T3. Bool fields count as answered** *(must)*
- Spec: `missing_fields` uses `is None` / missing-key checks. `consent_voice_clip=False` counts as answered.
- Accept: consent=False plus all other fields reaches READBACK.

**T4. Extraction prompt covers the spoken fields** *(must)*
- Spec: the prompt covers every voice-answered field (experience, food type, days, start time, duration, guests, price, city, area). **Do not extract `cancellation_rule`**: the policy is fixed (ARCHITECTURE.md §5.6) and only *stated* in the read-back. Landmark is stored as the raw transcript, and consent comes from YES/NO intent, so neither goes through extraction. Pass the validation error back on retry.
- Accept: the prompt mentions every voice-extracted field; `cancellation_rule` appears nowhere in `REQUIRED_FIELDS` or the prompt.

**T4b. Location pin replaces `location_shared`** *(must)*
- Spec: store `location_lat`, `location_lng` and `location_accuracy_m` from the Telegram `location` message.
  - Reject `venue`, forwarded messages, and pins more than `LOCATION_MAX_KM_FROM_CITY` from the city centre (haversine).
  - Show a share-location keyboard button.
  - Then ask for the landmark (voice → `landmark_hi`) and the gate photo (private media).
  - Migration adds the columns to `listings`; `location_shared` and `exact_address` are removed.
- Accept: pure tests for venue, forwarded, far-away and valid pins; the "location complete" check requires lat, lng, landmark and the proof photo.

**T5. Spoken haan/nahi during READBACK + consent answer** *(must)*
- Spec: in READBACK, classify intent instead of extracting. Keyword fast path (haan, ji, theek hai / nahi, galat), then LLM, with UNCLEAR on failure. YES → publish.
- Spec (consent): when the next missing field is `consent_voice_clip`, classify the reply the same way: YES → True, NO → False, UNCLEAR → ask again. No extraction.
- Accept: a unit test of the decision function (state + next field + transcript → action), covering both READBACK and consent.

**T6. CHANGE flow** *(must)*
- Spec: a keyword map (e.g. "daam" → price) → `session.change(field)` → re-ask that field → back to READBACK when it's filled.
- Accept: "daam badalna hai" in READBACK → COLLECTING with price missing.

**T7. One listing per host** *(must, changed)*
- Spec: when the state is DONE (listing LIVE) and the message isn't answering an open host prompt, reply "Aapka anubhav pehle se website pe hai." and **never** start a new session. ABANDONED + new message → fresh COLLECTING session.
- Accept: tests for both cases.

## Phase C — Listings become bookable
**T8. Store the full listing** *(must)*
- Spec: migration `0013` adds `duration_min, max_guests, available_weekdays (int[]), start_time_local, food_type, published_at` and drops the unused `cancellation_rule` column. `publish_listing` copies them across.
- Accept: migration up/down; publish sets all of them.

**T9. Slot generation on publish** *(must)*
- Spec: pure `generate_slots(weekdays, start_time_local, max_guests, today)` for the next 30 days, IST → UTC. Publish inserts the slots.
- Accept: tests for the weekday filter, IST→UTC and the 30-day bound.

**T10. English title/description on publish** *(must, was T25)*
- Spec: LLM writes `title_en` / `description_en` from the fields, validated with Pydantic, with a template English fallback if it fails. The landmark is translated to `landmark_en` (falls back to Hindi).
- Accept: tests with a mocked LLM for both success and fallback.

**T11. Listing page shows all upcoming slots** *(must)*
- Accept: one option per future slot with capacity.

## Phase D — Booking + payment correctness
**T12. Guard `/verify`** *(must)*: only HELD with an unexpired hold, else 409; uses `transition()`.
**T13. Fail button** *(must)*: `POST /pay/mock/{order}/fail` → payment FAILED, booking EXPIRED, seats released.
**T14. One hold implementation** *(must)*: `/book` uses `db_service.create_hold`; delete the duplicate; a single `SlotFullError`.

**T15. Host prompts, minimal** *(must, was T21)*
- Decision (Nov 9, demo scope): **no `host_prompts` table, no queue.** One pending booking per host: the host's PAID_PENDING_HOST booking *is* the open prompt. A second booking arriving meanwhile isn't asked about and times out to a refund via the existing job.
- Spec: verify sends a specific prompt (date, guests, payout). Text **and voice** haan/nahi are routed to the pending booking before onboarding: YES → CONFIRMED, NO → decline + refund, unclear → ask again.
- Accept: real-Postgres tests: paid booking + "haan" → CONFIRMED; "nahi" → REFUNDED; nothing pending → the T7 reply.

**T16. Location reveal on confirmation** *(must)*
- Spec: `/b/{token}` shows a Google Maps link (`https://www.google.com/maps?q=lat,lng`) and `landmark_en` **only** when CONFIRMED. The gate photo is never served.
- Accept: a template test for hidden vs shown.

**T17. Traveler cancel** *(must, new)*
- Spec: "Cancel booking" on `/b/{token}` before the start time → preview page with the refund amount from `booking/policy.py` (≥48h: 100%; <48h: 80%, host keeps 20%) → `POST` confirm → in one transaction: CANCELLED, refund row (unique per booking), ledger reversal entries, seats released → host voice note ("…aapko ₹600 milenge (test)" or "booking cancel ho gayi").
- Accept: policy math tests (including the exact 48h boundary and odd paise); double POST is a no-op; ledger balances after the cancel.

**T18. Host cancel by voice** *(should)*
- Spec: "booking cancel karni hai" → bot reads back which booking (CANCEL_CONFIRM prompt) → haan → CANCELLED, 100% refund, traveler email.
- Accept: a decision-function test.

**T19. Email outbox + SMTP** *(must, new)*
- Spec: an `email_outbox` table with `dedupe_key = "{booking_id}:{kind}"` unique, written **in the same transaction** as the status change. A job sends PENDING rows via stdlib `smtplib` (STARTTLS 587, timeout 15 s, run in a thread) with backoff, up to 5 attempts. Kinds: BOOKING_RECEIVED, BOOKING_CONFIRMED (map link, landmark, time, interpreter link, cancel link), BOOKING_CANCELLED (refund amount). Every email says TEST and never contains the host's phone or UPI ID.
- Accept: calling the status change twice gives exactly one row; a send failure moves to retry, then FAILED; a template test checks there's no location in RECEIVED and there is one in CONFIRMED.

**T20. Live status on the booking page** *(must, new)*
- Spec: `GET /b/{token}/status` returns JSON. The page polls every 5 s while PAID_PENDING_HOST and re-renders on change.
- Accept: manual browser check: the host says haan and the page flips to Confirmed.

## Phase E — Jobs
**T21. Scheduler survives errors** *(must)*: try/except + `logger.exception` per job.
**T22. Honor `payout_delay_minutes`** *(should)*
**T23. Payout voice note** *(should)*: template "₹X aapke UPI mein bhej diye (test)".

## Phase F — Interpreter
**T24. Token check** *(must)*: CONFIRMED and within ±12h of the slot start, else 403.
**T25. Interpreter page** *(must)*: two record buttons → turn endpoint → play the audio; show both texts. Log latency.

## Phase G — Demo readiness
**T26. Role-play labels + badges** *(must, was T26)*
- Spec: `is_demo_roleplay` is set from `DEMO_ROLEPLAY_TELEGRAM_IDS` at host creation. Listing cards and pages show "Demo host (role-play)". The badge reads "Location shared" (never "verified"). Experience photos are shown.
- Accept: template tests.

**T27. Deploy** *(must)*
- Spec: Dockerfile (Python 3.12 slim + ffmpeg + uv) → always-on host + managed Postgres, `BOT_MODE=webhook` with secret token, `/healthz`.
- Accept: the public URL serves `/`; a voice note to the bot works in webhook mode; a test booking email arrives.

## Cut → `docs/V2.md`
T17-old PAYOUT_QUERY, LLM search ranking (plain SQL filters are enough), voice_turns logging, persistent Gnani cap, Telegram send retries, demo voice-note script, arrival check / no-show, report a problem / disputes, UPI setup, reviews, hotel bundles.

## End-to-end check (after Phase D)
`docker compose up -d db && uv run alembic upgrade head && uv run uvicorn app.main:app`, then:
1. `/healthz` returns ok.
2. Onboard by voice, including pin, landmark, gate photo and photos.
3. The listing appears on `/` in English, labelled role-play, with slots.
4. Book → pay (TEST) → the host gets a voice note → host says **haan**.
5. `/b/{token}` flips to CONFIRMED live, with the map link, and the confirmation email arrives.
6. Cancel a second booking (<48h) → refund preview → cancelled → host voice note + cancellation email.