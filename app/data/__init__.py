"""Market-data adapters -> normalized Candle. Fixture provider works with no keys."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.types import Candle


class MarketDataProvider(Protocol):
    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]: ...


class FixtureProvider:
    """Deterministic synthetic candles so the whole system runs offline / keyless."""

    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        base = 100.0 + (hash(symbol) % 50)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        out: list[Candle] = []
        for i in range(limit):
            drift = (i % 20) - 10          # gentle oscillation, deterministic
            close = base + drift + (i * 0.05)
            out.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    ts=now + timedelta(minutes=i),
                    open=close - 0.5,
                    high=close + 1.0,
                    low=close - 1.0,
                    close=close,
                    volume=1000 + (i % 7) * 250,
                )
            )
        return out


# TODO(codex): CcxtProvider (crypto) and AlpacaProvider (equities, PAPER). Normalize both to
#              Candle. Cache + respect rate limits. Select via settings.market_data_provider.


def get_provider(name: str) -> MarketDataProvider:
    if name == "fixture":
        return FixtureProvider()
    raise NotImplementedError(f"provider '{name}' not implemented yet — see TODO(codex)")
