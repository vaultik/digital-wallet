# app/core/config.py
from typing import Optional

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

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    def database_url(self) -> str:
        """We construct the connection string dynamically."""
        return (
            f'postgresql+asyncpg://'
            f'{self.postgres_user}:{self.postgres_password}'
            f'@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}'
        )

    # Superuser
    redis_url: str = 'redis://localhost:6379'


settings = Settings()
