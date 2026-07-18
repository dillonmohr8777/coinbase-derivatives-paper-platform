"""Derivatives-oriented breakout strategy with volatility and funding filters."""

from __future__ import annotations

from statistics import fmean

from app.strategy.base import Strategy
from app.types import Candle, Side, Signal


class StrategyV2(Strategy):
    version = "strategy_v2"

    def __init__(self, lookback: int = 48, atr_window: int = 20) -> None:
        self.lookback = lookback
        self.atr_window = atr_window

    def generate_signals(self, candles: list[Candle], context: dict) -> list[Signal]:
        if len(candles) < max(self.lookback, self.atr_window) + 1:
            return []
        last = candles[-1]
        history = candles[-self.lookback - 1 : -1]
        returns = [
            abs(candles[i].close / candles[i - 1].close - 1)
            for i in range(len(candles) - self.atr_window, len(candles))
        ]
        realized_vol = fmean(returns)
        if not 0.0002 <= realized_vol <= 0.05:
            return []
        prior_high = max(c.high for c in history)
        prior_low = min(c.low for c in history)
        funding_rate = float(context.get("funding_rate", 0.0))
        side = None
        if last.close > prior_high and funding_rate < 0.001:
            side = Side.BUY
        elif last.close < prior_low and funding_rate > -0.001:
            side = Side.SELL
        if side is None:
            return []
        max_position = float(context.get("max_position_usd", 1000))
        risk_scale = min(max(realized_vol / 0.01, 0.25), 1.0)
        size = max_position * (1 - 0.5 * risk_scale) / last.close
        return [
            Signal(
                last.symbol,
                side,
                size,
                f"{self.lookback}-bar breakout; vol={realized_vol:.4f}; funding={funding_rate:.6f}",
                self.version,
                last.ts,
            )
        ]
