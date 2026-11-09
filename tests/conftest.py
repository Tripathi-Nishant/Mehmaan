"""Real-Postgres fixture. Uses a separate `mehmaan_test` database (never the dev one), built
with the real Alembic migrations once per run and emptied after every test.
Start it with `docker compose up -d db`; without it, `db` tests are skipped."""

import asyncio
import os

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DB = "mehmaan_test"
SERVER_DSN = os.getenv("TEST_PG_SERVER", "postgresql://mehmaan:mehmaan@localhost:5432/postgres")
TEST_URL = f"postgresql+asyncpg://mehmaan:mehmaan@localhost:5432/{TEST_DB}"


async def _create_test_db() -> None:
    conn = await asyncpg.connect(SERVER_DSN, timeout=3)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def migrated_test_db() -> str:
    try:
        asyncio.run(_create_test_db())
    except (OSError, asyncpg.PostgresError) as exc:
        pytest.skip(f"Postgres not reachable ({exc}); run `docker compose up -d db`")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_URL)
    command.upgrade(config, "head")
    return TEST_URL


@pytest.fixture
async def db(migrated_test_db: str):
    engine = create_async_engine(migrated_test_db, poolclass=NullPool)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    async with engine.begin() as conn:
        tables = await conn.scalar(
            text(
                "SELECT string_agg(quote_ident(tablename), ', ') FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        )
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    await engine.dispose()
