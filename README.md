# Mehmaan

Mehmaan is a solo build by Nancy: a voice-first marketplace for authentic local experiences in India.

The MVP uses Gnani Prisma for speech-to-text and Gnani Timbre for text-to-speech. Payments and payouts are mock-only for the challenge; no real payment provider is included.

## P0 setup

```bash
uv sync
Copy-Item .env.example .env
docker compose up -d db
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/smoke_gnani.py path/to/hindi.wav
```

The live Gnani smoke script needs `GNANI_API_KEY` and account-configured Timbre voice names in `.env`.
