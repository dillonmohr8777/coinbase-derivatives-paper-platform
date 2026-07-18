"""Market-data adapters -> normalized Candle. Fixture provider works with no keys."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Protocol

import httpx

from app.types import Candle, DerivativeProduct


class MarketDataProvider(Protocol):
    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]: ...


class FixtureProvider:
    """Deterministic synthetic candles so the whole system runs offline / keyless."""

    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        base = 100.0 + (int(sha256(symbol.encode()).hexdigest()[:8], 16) % 50)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        out: list[Candle] = []
        for i in range(limit):
            cycle = i % 48
            drift = cycle * 0.45 if cycle < 24 else (48 - cycle) * 0.45
            close = base + drift + (i * 0.025)
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


class CoinbasePublicProvider:
    """Read-only Coinbase Advanced Trade perpetual market-data adapter.

    It intentionally has no order methods and accepts no trading credentials. A caller may
    inject an ``httpx.Client`` for deterministic offline tests.
    """

    BASE_URL = "https://api.coinbase.com/api/v3/brokerage/market"
    GRANULARITIES = {
        "1m": ("ONE_MINUTE", 60),
        "5m": ("FIVE_MINUTE", 300),
        "15m": ("FIFTEEN_MINUTE", 900),
        "1h": ("ONE_HOUR", 3600),
        "1d": ("ONE_DAY", 86400),
    }

    def __init__(self, client: httpx.Client | None = None, timeout: float = 10.0) -> None:
        self.client = client or httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "whale-desk-paper/0.1", "Cache-Control": "no-cache"},
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        response = self.client.get(f"{self.BASE_URL}{path}", params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Coinbase returned an unexpected payload")
        return payload

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def list_perpetuals(self) -> list[DerivativeProduct]:
        payload = self._get(
            "/products",
            {"product_type": "FUTURE", "contract_expiry_type": "PERPETUAL", "limit": 250},
        )
        products: list[DerivativeProduct] = []
        for raw in payload.get("products", []):
            future = raw.get("future_product_details") or {}
            perp = future.get("perpetual_details") or {}
            interval = self._number(future.get("funding_interval"), 3600.0)
            if interval > 1_000_000_000:
                interval /= 1_000_000_000  # Coinbase may encode the interval in nanoseconds.
            products.append(
                DerivativeProduct(
                    product_id=str(raw["product_id"]),
                    display_name=str(raw.get("display_name") or raw["product_id"]),
                    price=self._number(raw.get("price") or raw.get("mid_market_price")),
                    best_bid=self._number(raw.get("best_bid_price")),
                    best_ask=self._number(raw.get("best_ask_price")),
                    base_increment=self._number(raw.get("base_increment"), 1e-8),
                    quote_increment=self._number(raw.get("quote_increment"), 0.01),
                    min_size=self._number(raw.get("base_min_size")),
                    open_interest=self._number(
                        perp.get("open_interest") or future.get("open_interest")
                    ),
                    funding_rate=self._number(
                        perp.get("funding_rate") or future.get("funding_rate")
                    ),
                    funding_interval_seconds=max(interval, 60.0),
                    max_leverage=self._number(perp.get("max_leverage"), 1.0),
                    index_price=self._number(future.get("index_price")),
                    trading_disabled=bool(raw.get("trading_disabled", False)),
                )
            )
        return products

    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        if timeframe not in self.GRANULARITIES:
            raise ValueError(f"unsupported Coinbase timeframe: {timeframe}")
        granularity, seconds = self.GRANULARITIES[timeframe]
        limit = min(max(limit, 1), 350)
        end = int(datetime.now(timezone.utc).timestamp())
        start = end - seconds * limit
        payload = self._get(
            f"/products/{symbol}/candles",
            {"start": str(start), "end": str(end), "granularity": granularity, "limit": limit},
        )
        candles = [
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                ts=datetime.fromtimestamp(int(row["start"]), timezone.utc),
                open=self._number(row["open"]),
                high=self._number(row["high"]),
                low=self._number(row["low"]),
                close=self._number(row["close"]),
                volume=self._number(row["volume"]),
            )
            for row in payload.get("candles", [])
        ]
        candles.sort(key=lambda candle: candle.ts)
        return candles


# TODO(codex): CcxtProvider (crypto) and AlpacaProvider (equities, PAPER). Normalize both to
#              Candle. Cache + respect rate limits. Select via settings.market_data_provider.


def get_provider(name: str) -> MarketDataProvider:
    if name == "fixture":
        return FixtureProvider()
    if name == "coinbase_public":
        return CoinbasePublicProvider()
    raise NotImplementedError(f"provider '{name}' not implemented yet — see TODO(codex)")
