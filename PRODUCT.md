# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Travelers (primary web user):** foreign travelers visiting India who want to spend time inside a real Indian home: cooking, a craft, music or culture with a local family. They browse, book, pay, get confirmation, find the home, and talk to the host on the day.
- **Hosts (Telegram, not the website):** Hindi-speaking home hosts with little or no tech experience. They never use the website; they list, confirm bookings, and hear about payouts through voice notes on a Telegram bot.
- **Challenge judges (evaluators):** the product is a challenge submission demoed on Nov 10, 2026. The site must make the concept clear and honest in a short demo.

## Product Purpose

Mehmaan lets homes that are invisible online welcome travelers as guests. A host describes their experience by voice; Mehmaan turns it into a bookable English listing with fixed dates and price. Success: a traveler books, the host says "haan" by voice, and the traveler arrives at the right door on the right day and can talk with the host.

## Positioning

Hosts list, confirm and manage everything **by voice, in Hindi, on Telegram**: no typing, no app, no English. A neighbouring product (Airbnb Experiences, tour sites) requires literate, online hosts; Mehmaan's supply is homes those products cannot reach. Pitch line: "Atithi Devo Bhava: in India, the guest is God. Millions of homes live this every day, but they're invisible online. Mehmaan lets them welcome the world, in their own voice."

## Operating Context

- Host flow (Telegram voice): onboarding questions → location pin + spoken landmark + private gate photo → read-back → "haan" publishes. Booking requests arrive as a Hindi voice note; the host answers haan/nahi by voice or text.
- Traveler flow (web): browse `/` → listing `/listings/{id}` → pick slot + guests → TEST payment → booking page `/b/{token}` (status, map + landmark only after confirmation, cancel) → emails (received, confirmed, cancelled) → interpreter on the day.
- Stack: FastAPI + Jinja2 server-rendered pages, Postgres, Gnani speech-to-text / text-to-speech, an LLM for extraction and English copy.

## Capabilities and Constraints

- **Payments are TEST only.** No real money moves; every money screen and email says TEST.
- **Fixed cancellation policy:** full refund 48 hours or more before start; later, 80% back and the host keeps 20%. Not cancellable after start.
- **Location privacy:** exact pin and landmark are shown only after the host confirms; the gate photo is never shown publicly.
- **Demo hosts are role-play** and must be labelled "Demo host (role-play)". The location badge reads "Location shared", never "verified".
- Cities: within 50 km of known city centres; categories: food, craft, music, culture.
- Deadline: submit Nov 10, 2026 evening. Plain working pages beat unfinished beautiful ones.
- Not built yet (as of this file): live booking status, interpreter page, deploy.

## Brand Commitments

- Name: Mehmaan (मेहमान, "guest"). Concept: अतिथि देवो भव, presented as Indian hospitality shared across families and faiths, never as a religious ritual; never imitate Ministry of Tourism branding.
- Voice: warm and simple, like a host. Respectful "aap"/"ji". A few Hindi words with English beside them. Short sentences.
- **Entrance door: an authentic traditional Indian door, based on a reference picture the user will provide.**
- **Experience imagery: only real photos, provided by the user later.** Until then, placeholders must read as placeholders, not as photos of real homes.
- Visual specification is in `docs/DESIGN.md` (approved 2026-11-09).

## Evidence on Hand

- None real yet: no host photos, no voice clips, no testimonials, no reviews, no usage numbers. Never invent any of these.
- Coming from the user: the door reference picture; real experience photos.
- Local demo data: three role-play listings (Meena, Ramesh, Shabnam) seeded in the developer's database for design review only.

## Product Principles

1. **The host's own voice is the thread.** What the host said, in their words, comes before marketing copy.
2. **Honest by default.** TEST, role-play and placeholder states are always visible; no invented proof.
3. **Trust before the ask.** Price, refund rules and what happens next are clear before any payment.
4. **The guest is welcomed, not sold to.** Hospitality language and moments (welcome, confirmation, goodbye) over conversion tricks.
5. **Working beats beautiful under the deadline.**

## Accessibility & Inclusion

- WCAG AA contrast (palette in `docs/DESIGN.md` is contrast-checked); status never by colour alone.
- Respect `prefers-reduced-motion` for all motion, including the door entrance and petals.
- Works at 390 px phone width; travelers book on phones.
- Bilingual text (Hindi + English) must render correctly; mark Hindi with `lang="hi"`.
