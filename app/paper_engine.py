"""Continuous, paper-only derivatives engine with persistent reconciliation state."""

from __future__ import annotations

import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.data import CoinbasePublicProvider, MarketDataProvider, get_provider
from app.execution import DerivativesPaperBroker
from app.guardrails import GuardrailError, check_risk_limits, require_fresh_data
from app.memory import Memory, get_memory
from app.strategy import get_strategy
from config.settings import get_settings, load_yaml_config


class PaperEngine:
    def __init__(
        self,
        provider: MarketDataProvider,
        memory: Memory,
        broker: DerivativesPaperBroker,
        *,
        symbols: list[str],
        timeframe: str = "5m",
        strategy_version: str = "strategy_v2",
        risk: dict | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.provider = provider
        self.memory = memory
        self.broker = broker
        self.symbols = symbols
        self.timeframe = timeframe
        self.strategy = get_strategy(strategy_version)
        self.risk = risk or {
            "max_position_usd": 1000,
            "max_concurrent_positions": 5,
            "daily_loss_stop_usd": 500,
        }
        self.logger = logger or (lambda message: print(message, flush=True))
        self.day_start_equity = broker.equity
        self.session_day = datetime.now(timezone.utc).date()
        self.last_funding: dict[str, datetime] = {}

    def log(self, message: str) -> None:
        line = f"{datetime.now(timezone.utc).isoformat()}  {message}"
        self.logger(line)
        self.memory.write("runlog", {"message": line})

    def tick(self) -> dict:
        now = datetime.now(timezone.utc)
        if Path("STOP").exists():
            self.log("HALT kill switch STOP is present; no market processing")
            return self.broker.snapshot()
        if now.date() != self.session_day:
            self.session_day = now.date()
            self.day_start_equity = self.broker.equity
            self.log(f"RISK new UTC session day; start_equity={self.day_start_equity:.2f}")
        for symbol in self.symbols:
            try:
                candles = self.provider.get_candles(symbol, self.timeframe, 250)
                if isinstance(self.provider, CoinbasePublicProvider):
                    require_fresh_data(candles, datetime.now(timezone.utc), 900)
                if not candles:
                    raise GuardrailError("market data unavailable")
                self.broker.mark(symbol, candles[-1].close)
                funding_rate = 0.0
                funding_interval = 3600.0
                if isinstance(self.provider, CoinbasePublicProvider):
                    products = {
                        product.product_id: product for product in self.provider.list_perpetuals()
                    }
                    product = products.get(symbol)
                    if product:
                        funding_rate = product.funding_rate
                        funding_interval = product.funding_interval_seconds
                now = datetime.now(timezone.utc)
                previous_funding = self.last_funding.setdefault(symbol, now)
                if (now - previous_funding).total_seconds() >= funding_interval:
                    payment = self.broker.apply_funding(symbol, funding_rate)
                    self.last_funding[symbol] = now
                    if payment:
                        self.log(f"FUNDING {symbol} payment={payment:.4f} rate={funding_rate:.8f}")
                self.log(f"DATA {symbol} candles={len(candles)} close={candles[-1].close:.4f}")
                signals = self.strategy.generate_signals(
                    candles,
                    {
                        "max_position_usd": self.risk["max_position_usd"],
                        "funding_rate": funding_rate,
                        "memory": self.memory.search(symbol, 5),
                    },
                )
                for signal in signals:
                    check_risk_limits(
                        signal,
                        candles[-1].close,
                        len(self.broker.positions),
                        self.broker.equity - self.day_start_equity,
                        max_position_usd=self.risk["max_position_usd"],
                        max_concurrent_positions=self.risk["max_concurrent_positions"],
                        daily_loss_stop_usd=self.risk["daily_loss_stop_usd"],
                    )
                    fill = self.broker.place_order(signal, candles[-1].close)
                    record = {
                        "time": fill.ts.isoformat(),
                        "symbol": fill.symbol,
                        "action": fill.side.value,
                        "qty": fill.qty,
                        "price": fill.price,
                        "fee": fill.fee,
                        "strategy": signal.strategy_version,
                    }
                    self.memory.write("trade", record)
                    self.log(
                        f"{signal.strategy_version.upper()} {fill.side.value} {symbol} "
                        f"qty={fill.qty:.6f} price={fill.price:.4f} PAPER"
                    )
            except Exception as exc:
                # Adapter and validation errors fail closed for this tick.
                self.log(f"HALT {symbol}: {type(exc).__name__}: {exc}")
        snapshot = self.broker.snapshot()
        self.memory.write("portfolio", snapshot)
        self.log(
            f"PORTFOLIO equity={snapshot['equity']:.2f} gross={snapshot['gross_notional']:.2f} "
            f"buffer={snapshot['liquidation_buffer']:.2f}"
        )
        return snapshot

    def run_forever(self, interval_seconds: int = 60) -> None:
        self.log(f"paper engine started: {', '.join(self.symbols)}")
        while True:
            self.tick()
            time.sleep(max(interval_seconds, 5))


def main() -> None:
    parser = argparse.ArgumentParser(description="paper-only Coinbase derivatives engine")
    parser.add_argument("--once", action="store_true", help="run one reconciled tick and exit")
    args = parser.parse_args()
    settings = get_settings()
    if settings.live_enabled:
        raise SystemExit("Refusing to start: continuous engine is paper-only")
    cfg = load_yaml_config()
    provider = get_provider(settings.market_data_provider)
    symbols = cfg.get("derivatives", {}).get("products") or cfg["watchlist"]["crypto"]
    engine = PaperEngine(
        provider,
        get_memory(settings),
        DerivativesPaperBroker(
            starting_equity=cfg.get("paper", {}).get("starting_equity", 10_000),
            fee_bps=cfg["execution"]["fee_bps"],
            slippage_bps=cfg["execution"]["slippage_bps"],
            max_leverage=cfg.get("paper", {}).get("max_leverage", 3),
        ),
        symbols=symbols,
        timeframe=cfg.get("derivatives", {}).get("timeframe", "5m"),
        strategy_version=cfg["strategy"].get("derivatives_active", "strategy_v2"),
        risk=cfg["risk"],
    )
    if args.once:
        engine.tick()
    else:
        engine.run_forever(cfg.get("paper", {}).get("poll_seconds", 60))


if __name__ == "__main__":
    main()
