"""
Susu Books - Configuration Settings
Centralizes all configurable values using pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from functools import lru_cache


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # Application
    app_name: str = "Susu Books"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = f"sqlite:///{BASE_DIR}/susu_books.db"
    db_echo: bool = False  # Set True for SQL query logging

    # Ollama / Gemma 4
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:31b-instruct"
    ollama_timeout: int = 120  # seconds
    ollama_max_retries: int = 3

    # Default currency and locale
    default_currency: str = "GHS"
    default_language: str = "en"

    # Supported languages (ISO 639-1 codes + locale variants)
    supported_languages: list[str] = ["en", "tw", "ha", "pcm", "sw"]

    # Inventory
    default_low_stock_threshold: float = 5.0

    # CORS — allow frontend dev server
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

    # File upload limits
    max_image_size_mb: int = 10

    # Credit profile default window
    credit_profile_days: int = 180

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
