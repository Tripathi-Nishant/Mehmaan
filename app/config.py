from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://mehmaan:mehmaan@localhost:5432/mehmaan"
    public_base_url: str = "http://localhost:8000"
    gnani_api_key: str = ""
    gnani_base_url: str = "https://api.vachana.ai"
    gnani_stt_model: str = "prisma-v2.5"
    gnani_tts_model: str = "timbre-v2.5"
    gnani_tts_voice_hi: str = ""
    gnani_tts_voice_en: str = ""
    gnani_daily_call_cap: int = 800
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    bot_mode: str = "polling"
    commission_bps: int = 1500
    mock_payment_secret: str = "change-me"
    hold_minutes: int = 15
    host_reply_timeout_minutes: int = 720
    payout_delay_minutes: int = 1440
    location_max_km_from_city: float = 50
    smtp_host: str = ""  # empty: emails stay queued (PENDING), nothing is sent
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Mehmaan TEST <no-reply@example.com>"
    log_level: str = "INFO"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
