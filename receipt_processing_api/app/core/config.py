"""Simple configuration management.

This module defines a ``Settings`` class that reads configuration
values from environment variables and provides sensible defaults.
It avoids depending on ``pydantic-settings`` so that the API can
run in constrained environments without extra dependencies. If
``.env`` support is needed you can implement it here by reading the
file manually or using ``dotenv``.
"""


from __future__ import annotations

# dotenv_path = os.path.join(os.path.dirname(__file__), '../../.env')

import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

from pathlib import Path
from typing import Optional


class Settings:
    """Container for configuration values."""

    def __init__(self) -> None:
        # Basic application metadata
        self.APP_NAME: str = os.getenv("APP_NAME", "Receipt Processing API")
        self.ENV: str = os.getenv("ENV", "development")

        # Database configuration; use env var
        self.DATABASE_URL: str = os.getenv("DATABASE_URL")

        # API keys
        self.OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

        # Storage directory
        default_storage = Path(__file__).resolve().parent.parent.parent / "storage"
        self.STORAGE_DIRECTORY: str = os.getenv("STORAGE_DIRECTORY", str(default_storage))

        # Billing and secret keys
        self.STRIPE_API_KEY: Optional[str] = os.getenv("STRIPE_API_KEY")
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # one week


settings = Settings()