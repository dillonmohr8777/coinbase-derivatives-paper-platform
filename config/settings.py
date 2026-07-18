"""Central settings: env (secrets/toggles) + config.yaml (watchlist/params)."""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ROOT / ".env"), extra="ignore")

    # Safety gates — both default OFF for live.
    trading_mode: str = "paper"          # paper | live
    allow_live_orders: bool = False

    # LLM
    llm_provider: str = "mock"
    llm_model: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Market data / broker
    market_data_provider: str = "fixture"
    coinbase_public_base_url: str = "https://api.coinbase.com"
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper_base_url: str = "https://paper-api.alpaca.markets"

    # Alt-data
    options_flow_provider: str = "fixture"
    dark_pool_provider: str = "fixture"
    sec_edgar_user_agent: str = ""

    # Memory
    memory_backend: str = "local"        # local | cloud
    database_url: str = ""

    @property
    def live_enabled(self) -> bool:
        """A live order path is allowed ONLY if both gates are set. v1 keeps this False."""
        return self.trading_mode == "live" and self.allow_live_orders


def load_yaml_config() -> dict:
    path = _ROOT / "config" / "config.yaml"
    if not path.exists():
        path = _ROOT / "config" / "config.example.yaml"
    return yaml.safe_load(path.read_text())


@lru_cache
def get_settings() -> Settings:
    return Settings()
