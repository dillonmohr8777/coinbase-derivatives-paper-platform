"""Execution: PAPER broker + cost model. Live path is gated off in v1 (spec §3.6)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.guardrails import model_costs
from app.types import Fill, Signal


class Broker(Protocol):
    def place_order(self, signal: Signal, price: float) -> Fill: ...


class PaperBroker:
    """Simulated fills with modeled fees + slippage. Never touches real money."""

    def __init__(self, fee_bps: float = 10, slippage_bps: float = 5) -> None:
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps

    def place_order(self, signal: Signal, price: float) -> Fill:
        notional = signal.size * price
        cost = model_costs(notional, self.fee_bps, self.slippage_bps)
        slip = price * self.slippage_bps / 10_000.0
        fill_price = price + slip if signal.side.value == "BUY" else price - slip
        return Fill(
            symbol=signal.symbol,
            side=signal.side,
            qty=signal.size,
            price=fill_price,
            fee=cost,
            ts=datetime.now(timezone.utc),
            paper=True,
        )


def get_broker(settings) -> Broker:
    if settings.live_enabled:
        # TODO(codex): a real live broker MAY live here but stays UNREACHABLE in v1.
        # Do not implement/enable it. Fail loudly so it can't ship by accident.
        raise RuntimeError("live trading is out of scope for v1 — keep TRADING_MODE=paper")
    return PaperBroker()
