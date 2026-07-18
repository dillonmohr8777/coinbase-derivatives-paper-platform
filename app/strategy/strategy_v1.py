"""Baseline: moving-average crossover with a volume filter.

Mirrors the source video's reference to a 'crossover loss during low-volume chop' — the volume
filter is exactly the mitigation for that failure mode.
"""
from __future__ import annotations

from app.strategy.base import Strategy
from app.guardrails import liquidity_ok
from app.types import Candle, Side, Signal


class StrategyV1(Strategy):
    version = "strategy_v1"

    def __init__(self, fast: int = 9, slow: int = 21, min_volume_percentile: float = 40) -> None:
        self.fast = fast
        self.slow = slow
        self.min_volume_percentile = min_volume_percentile

    def _sma(self, closes: list[float], n: int) -> float | None:
        return sum(closes[-n:]) / n if len(closes) >= n else None

    def generate_signals(self, candles: list[Candle], context: dict) -> list[Signal]:
        if len(candles) < self.slow + 1:
            return []
        closes = [c.close for c in candles]
        vols = [c.volume for c in candles]

        fast_now, slow_now = self._sma(closes, self.fast), self._sma(closes, self.slow)
        fast_prev = self._sma(closes[:-1], self.fast)
        slow_prev = self._sma(closes[:-1], self.slow)
        if None in (fast_now, slow_now, fast_prev, slow_prev):
            return []

        last = candles[-1]
        if not liquidity_ok(vols[:-1], last.volume, self.min_volume_percentile):
            return []  # low-volume chop — skip (the video's failure example)

        # Cross up -> BUY, cross down -> SELL.
        side: Side | None = None
        if fast_prev <= slow_prev and fast_now > slow_now:  # type: ignore[operator]
            side = Side.BUY
        elif fast_prev >= slow_prev and fast_now < slow_now:  # type: ignore[operator]
            side = Side.SELL
        if side is None:
            return []

        max_position_usd = float(context.get("max_position_usd", 1000.0))
        risk_fraction = float(context.get("signal_risk_fraction", 0.25))
        size = max_position_usd * risk_fraction / last.close
        return [
            Signal(
                symbol=last.symbol,
                side=side,
                size=size,
                rationale=f"{self.fast}/{self.slow} MA cross {side.value} at {last.close:.2f}",
                strategy_version=self.version,
                ts=last.ts,
            )
        ]
