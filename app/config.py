# --------------------------------------
# App configuration
# --------------------------------------
# Reads settings from environment variables / a local .env file so secrets
# (DB password, JWT signing key) never get hard-coded into source.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
