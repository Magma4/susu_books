"""Susu Books configuration."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # Application
    app_name: str = "Susu Books"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    api_docs_enabled: bool = True
    security_headers_enabled: bool = True

    # Database
    database_url: str = f"sqlite:///{BASE_DIR}/susu_books.db"
    db_echo: bool = False  # Set True for SQL query logging

    # Ollama / Gemma 4
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:31b-instruct"
    ollama_timeout: int = 300  # seconds
    ollama_max_retries: int = 3

    # AI parameters tuned for extraction consistency rather than prose generation.
    ai_temperature: float = 0.1
    ai_top_p: float = 0.85
    ai_top_k: int = 30

    # Default currency and locale
    default_currency: str = "GHS"
    default_language: str = "en"

    # Supported languages (ISO 639-1 codes + locale variants)
    supported_languages: list[str] = Field(
        default_factory=lambda: ["en", "tw", "ha", "pcm", "sw"]
    )

    # Inventory
    default_low_stock_threshold: float = 5.0

    # CORS — allow frontend dev server
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
    )
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "*.localhost", "testserver"]
    )

    # File upload limits
    max_image_size_mb: int = 10

    # Credit profile default window
    credit_profile_days: int = 180
    export_max_rows: int = 10000

    # Abuse prevention for public deployments
    chat_rate_limit_requests: int = 30
    chat_rate_limit_window_seconds: int = 60

    @field_validator("supported_languages", "cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def _parse_list_settings(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return [str(value).strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
