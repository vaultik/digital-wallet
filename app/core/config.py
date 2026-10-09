# app/core/config.py
from typing import Literal, Optional

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment variables."""

    # Database
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int

    # JWT Secret
    secret: str

    # Superuser
    first_superuser_email: Optional[EmailStr] = None
    first_superuser_phone: Optional[str] = None
    first_superuser_password: Optional[str] = None

    # Redis
    redis_url: str = 'redis://localhost:6379'

    # Tests
    postgres_db_test: str = 'wallet_test'

    # Environment
    environment: Literal['local', 'production'] = 'local'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    def database_url(self) -> str:
        """We construct the connection string dynamically."""
        return (
            f'postgresql+asyncpg://'
            f'{self.postgres_user}:{self.postgres_password}'
            f'@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}'
        )

    @property
    def test_database_url(self) -> str:
        """Connection string for the isolated test database."""
        return (
            f'postgresql+asyncpg://'
            f'{self.postgres_user}:{self.postgres_password}'
            f'@{self.postgres_host}:{self.postgres_port}/{self.postgres_db_test}'
        )

    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_success_url: str = 'http://localhost:8000/deposit/success'
    stripe_cancel_url: str = 'http://localhost:8000/deposit/cancel'


settings = Settings()
