"""Application configuration.

All settings are read from the environment (or an optional ``.env`` file).
No credentials are ever hard-coded — see ``.env.example`` for the full list
of supported variables.
"""
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # Async SQLAlchemy connection string, e.g.
    # postgresql+asyncpg://user:password@host:5432/dbname
    DB_URL: str = Field(..., env="DB_URL")

    # Redis connection string, e.g. redis://localhost:6379/
    REDIS_URL: str = Field("redis://localhost:6379/", env="REDIS_URL")

    # Minimum cross-exchange spread (in %) worth persisting as an opportunity.
    SPREAD_THRESHOLD: float = Field(0.5, env="SPREAD_THRESHOLD")

    DEBUG: bool = Field(False, env="DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
