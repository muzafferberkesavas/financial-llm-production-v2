from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_DIR = BACKEND_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    ai_gateway_api_key: str | None = Field(default=None, alias="AI_GATEWAY_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")

    finnhub_api_key: str | None = Field(default=None, alias="FINNHUB_API_KEY")
    alpha_vantage_api_key: str | None = Field(default=None, alias="ALPHA_VANTAGE_API_KEY")
    newsapi_key: str | None = Field(default=None, alias="NEWSAPI_KEY")
    polygon_api_key: str | None = Field(default=None, alias="POLYGON_API_KEY")

    # Telegram (Phase 2.3)
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_channel_nasdaq: str | None = Field(default=None, alias="TELEGRAM_CHANNEL_NASDAQ")
    telegram_channel_bist: str | None = Field(default=None, alias="TELEGRAM_CHANNEL_BIST")
    telegram_admin_ids: str | None = Field(default=None, alias="TELEGRAM_ADMIN_IDS")

    database_url: str = Field(
        default=f"duckdb:///{(DATA_DIR / 'finllm.duckdb').resolve()}",
        alias="DATABASE_URL",
    )

    portfolio_initial_capital_usd: float = Field(
        default=10000.0, alias="PORTFOLIO_INITIAL_CAPITAL_USD"
    )

    # === Reasoning ===
    # "single" = sadece Claude (ucuz, hızlı), "ensemble" = Claude+GPT+Gemini voting
    reasoner_mode: str = Field(default="ensemble", alias="REASONER_MODE")

    # === Sentiment provider ===
    # "finbert" = lokal FinBERT (Mac MPS), "fingpt" = uzak FinGPT (AWS endpoint)
    sentiment_provider: str = Field(default="finbert", alias="SENTIMENT_PROVIDER")
    fingpt_endpoint: str | None = Field(default=None, alias="FINGPT_ENDPOINT")
    fingpt_api_key: str | None = Field(default=None, alias="FINGPT_API_KEY")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    env: str = Field(default="development", alias="ENV")

    @property
    def raw_dir(self) -> Path:
        d = DATA_DIR / "raw"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def processed_dir(self) -> Path:
        d = DATA_DIR / "processed"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def cache_dir(self) -> Path:
        d = DATA_DIR / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d


settings = Settings()
