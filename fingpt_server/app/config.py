from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[1] / ".env",
        extra="ignore",
    )

    fingpt_api_key: str | None = Field(default=None, alias="FINGPT_API_KEY")
    device: str = Field(default="auto", alias="DEVICE")
    load_in_4bit: bool = Field(default=True, alias="LOAD_IN_4BIT")

    sentiment_model: str = Field(
        default="FinGPT/fingpt-mt_llama2-7b_lora",
        alias="SENTIMENT_MODEL",
    )
    forecaster_model: str = Field(
        default="FinGPT/fingpt-forecaster_dow30_llama2-7b_lora",
        alias="FORECASTER_MODEL",
    )
    base_llama_model: str = Field(
        default="meta-llama/Llama-2-7b-chat-hf",
        alias="BASE_LLAMA_MODEL",
    )
    hf_token: str | None = Field(default=None, alias="HF_TOKEN")
    rag_index_dir: str = Field(default="/opt/fingpt/rag_index", alias="RAG_INDEX_DIR")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


settings = Settings()
