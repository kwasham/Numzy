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
        # Dramatiq/Redis configuration
        self.DRAMATIQ_BROKER_URL = os.getenv("DRAMATIQ_BROKER_URL", "redis://localhost:6379/0")

        # Basic application metadata
        self.APP_NAME = os.getenv("APP_NAME", "Receipt Processing API")
        self.ENV = os.getenv("ENV", "development")

        # Database configuration; use env var
        self.DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db/numzy")

        # API keys
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

        # Storage directory
        default_storage = Path(__file__).resolve().parent.parent.parent / "storage"
        self.STORAGE_DIRECTORY = os.getenv("STORAGE_DIRECTORY", str(default_storage))

        self.DEV_AUTH_BYPASS = os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true"

        # Billing and secret keys
        self.STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
        self.SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # one week


settings = Settings()