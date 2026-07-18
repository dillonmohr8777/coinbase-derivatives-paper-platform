"""Guardrails — 'Why most bots fail' (Source A, 3:32). Bake safety in before features.

Each function is intentionally small and unit-tested (tests/test_guardrails.py). The
orchestrator MUST call these before any order is placed.
"""
from __future__ import annotations

from app.types import Candle, Signal


class GuardrailError(Exception):
    """Raised to HALT new orders (fail-safe) rather than trade on bad state."""


def no_lookahead(visible: list[Candle], decision_ts) -> None:
    """Reject if any candle used for a decision is at/after decision time."""
    if any(c.ts >= decision_ts for c in visible):
        raise GuardrailError("look-ahead bias: future candle visible at decision time")


def model_costs(notional: float, fee_bps: float, slippage_bps: float) -> float:
    """Return total modeled cost (fees + slippage). Must be applied to every fill."""
    return notional * (fee_bps + slippage_bps) / 10_000.0


def check_risk_limits(
    signal: Signal,
    price: float,
    open_positions: int,
    day_pnl: float,
    *,
    max_position_usd: float,
    max_concurrent_positions: int,
    daily_loss_stop_usd: float,
) -> None:
    if signal.size * price > max_position_usd:
        raise GuardrailError("position exceeds max_position_usd")
    if open_positions >= max_concurrent_positions:
        raise GuardrailError("max_concurrent_positions reached")
    if day_pnl <= -abs(daily_loss_stop_usd):
        raise GuardrailError("daily loss stop hit — halting new orders")


def liquidity_ok(recent_volumes: list[float], current_volume: float, min_percentile: float) -> bool:
    """Skip signals during low-volume chop (the video's own failure example)."""
    if not recent_volumes:
        return True
    ranked = sorted(recent_volumes)
    idx = int(len(ranked) * min_percentile / 100.0)
    threshold = ranked[min(idx, len(ranked) - 1)]
    return current_volume >= threshold


def overfitting_ok(
    train_return: float,
    validation_return: float,
    *,
    max_degradation: float = 0.70,
) -> bool:
    """Require positive held-out performance that does not collapse vs training."""
    if train_return <= 0 or validation_return <= 0:
        return False
    return validation_return / train_return >= 1.0 - max_degradation


def require_fresh_data(candles: list[Candle], now, max_age_seconds: float) -> None:
    """Fail closed on missing, partial, unordered, or stale market data."""
    if not candles:
        raise GuardrailError("market data unavailable")
    if any(b.ts <= a.ts for a, b in zip(candles, candles[1:])):
        raise GuardrailError("market data is unordered or duplicated")
    age = (now - candles[-1].ts).total_seconds()
    if age < 0 or age > max_age_seconds:
        raise GuardrailError("market data is stale")
