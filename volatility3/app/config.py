from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://vol:vol@localhost:5432/vol_gui"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: str = "./data"
    volatility3_offline: bool = False
    cors_allow_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Insights (optional, profile-gated - see docker-compose.yml). No "enabled"
    # flag on purpose: reachability of this URL *is* the enabled/disabled
    # signal, so there's only one thing to keep in sync, not two.
    insights_base_url: str = "http://insights:8100"
    insights_health_timeout_seconds: float = 3.0
    # Must exceed insights' own OLLAMA_TIMEOUT_SECONDS (280s default) or the
    # backend would give up on a request that was still going to succeed.
    # CPU-only inference of a real 5-plugin triage bundle genuinely takes a
    # few minutes - measured directly, not a guess (see baseline.py).
    insights_summarize_timeout_seconds: float = 320.0

    # volatility2 (the "legacy engine" compose service, for images v3's
    # automagic can't handle) - always on, unlike Insights: no multi-GB
    # model weights, no heavy resource cost, and it's core analysis
    # capability rather than an optional AI layer. See volatility2/README.md.
    volatility2_base_url: str = "http://volatility2:8200"
    legacy_health_timeout_seconds: float = 3.0
    legacy_run_timeout_seconds: float = 620.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
