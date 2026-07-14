from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    DB_URL: str = Field(..., env="DB_URL")
    REDIS_URL: str = Field("redis://localhost:6379/", env="REDIS_URL")
    SPREAD_THRESHOLD: float = Field(0.5, env="SPREAD_THRESHOLD")
    DEBUG: bool = Field(False, env="DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
