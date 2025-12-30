"""Configuration management."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration."""

    # Stripe
    stripe_api_key: str
    stripe_price_monthly: str
    stripe_price_annual: str
    stripe_webhook_secret: str
    stripe_payment_link: str

    # App settings
    app_env: str
    app_url: str
    debug: bool

    # Data settings
    months_ahead: int = 3
    max_market_cap: float = 5_000_000_000  # $5B
    cache_ttl_hours: int = 24

    # n8n
    n8n_webhook_base_url: Optional[str] = None

    @classmethod
    def from_env(cls, env_file: Optional[Union[str, Path]] = None) -> "Config":
        """Load configuration from environment variables.

        Args:
            env_file: Path to .env file (optional)

        Returns:
            Config instance
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        return cls(
            stripe_api_key=os.getenv("STRIPE_API_KEY", ""),
            stripe_price_monthly=os.getenv("STRIPE_PRICE_MONTHLY", ""),
            stripe_price_annual=os.getenv("STRIPE_PRICE_ANNUAL", ""),
            stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
            stripe_payment_link=os.getenv("STRIPE_PAYMENT_LINK", ""),
            app_env=os.getenv("APP_ENV", "development"),
            app_url=os.getenv("APP_URL", "http://localhost:8501"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            n8n_webhook_base_url=os.getenv("N8N_WEBHOOK_BASE_URL"),
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is configured."""
        return bool(self.stripe_api_key and self.stripe_price_monthly and self.stripe_price_annual)
