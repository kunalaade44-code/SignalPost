import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

is_vercel = bool(os.environ.get("VERCEL"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General
    app_name: str = "Signalpost"
    app_env: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Limits & Budget (Enforced hard constraints)
    max_requests_total: int = 2000
    max_cost_usd: float = 10.0
    max_run_time_seconds: int = 2700  # 45 minutes
    request_budget_per_company: int = 18

    # LLM Settings (provider-agnostic, supporting Mistral AI free tier)
    model_name: str = "mistral-small-latest"
    api_key: str = ""
    mistral_api_key: str = ""
    llm_provider: str = "mistral"

    # Brreg Endpoints
    brreg_enheter_base_url: str = "https://data.brreg.no/enhetsregisteret/api"
    brreg_regnskap_base_url: str = "https://data.brreg.no/regnskapsregisteret/regnskap"
    user_agent: str = (
        "Signalpost-Agent/1.0 (+https://github.com/builderr-signalpost/signalpost; bot@signalpost.ai)"
    )

    # Database & Storage (SQLite local fallback or Supabase PostgreSQL)
    database_url: str = "sqlite:////tmp/signalpost.db" if is_vercel else "sqlite:///./signalpost.db"
    supabase_url: str = ""
    supabase_key: str = ""
    cache_dir: Path = Path("/tmp/cache" if is_vercel else "./cache")
    cache_enabled: bool = True
    cache_ttl_days_registry: int = 7
    cache_ttl_days_website: int = 30

    # Output Directory
    out_dir: Path = Path("/tmp/out" if is_vercel else "./out")


settings = Settings()
