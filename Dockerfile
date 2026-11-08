FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .env.example ./
EXPOSE 8000
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
