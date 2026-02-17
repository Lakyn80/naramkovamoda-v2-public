from functools import lru_cache
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "naramkovamoda-v2"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    api_prefix: str = "/api"
    expose_invoice_api: bool = False
    database_url: str = Field(
        ...,
        validation_alias=AliasChoices("DATABASE_URL", "NMM_DATABASE_URL"),
    )
    # CORS: čárkou oddělené origins, nebo prázdné = použijí se výchozí localhost porty
    cors_origins: str = ""

    model_config = SettingsConfigDict(env_prefix="NMM_", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
