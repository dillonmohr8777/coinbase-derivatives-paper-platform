"""Anchored walk-forward evaluation for versioned strategies."""

from __future__ import annotations

from dataclasses import dataclass

from app.eval import compute_metrics
from app.execution import PaperBroker
from app.guardrails import overfitting_ok
from app.strategy.base import Strategy
from app.types import Candle, Metrics, Side


@dataclass(frozen=True)
class WalkForwardFold:
    train: Metrics
    validation: Metrics
    accepted: bool


@dataclass(frozen=True)
class WalkForwardReport:
    strategy_version: str
    folds: list[WalkForwardFold]
    accepted: bool


def _evaluate(
    strategy: Strategy, candles: list[Candle], fee_bps: float, slippage_bps: float
) -> Metrics:
    broker = PaperBroker(fee_bps, slippage_bps)
    entry = None
    pnls: list[float] = []
    for index in range(len(candles)):
        visible = candles[: index + 1]
        for signal in strategy.generate_signals(visible, {"max_position_usd": 1000}):
            fill = broker.place_order(signal, visible[-1].close)
            if signal.side is Side.BUY and entry is None:
                entry = (fill.price, fill.qty, fill.fee)
            elif signal.side is Side.SELL and entry is not None:
                price, qty, fee = entry
                pnls.append((fill.price - price) * min(qty, fill.qty) - fee - fill.fee)
                entry = None
    return compute_metrics(pnls)


def walk_forward(
    strategy: Strategy,
    candles: list[Candle],
    *,
    folds: int = 3,
    fee_bps: float = 10,
    slippage_bps: float = 5,
) -> WalkForwardReport:
    if folds < 2 or len(candles) < folds * 100:
        raise ValueError("walk-forward evaluation needs at least 100 candles per fold")
    step = len(candles) // (folds + 1)
    results = []
    for fold in range(1, folds + 1):
        train = candles[: step * fold]
        validation = candles[step * fold : step * (fold + 1)]
        train_metrics = _evaluate(strategy, train, fee_bps, slippage_bps)
        validation_metrics = _evaluate(strategy, validation, fee_bps, slippage_bps)
        accepted = overfitting_ok(train_metrics.total_return, validation_metrics.total_return)
        results.append(WalkForwardFold(train_metrics, validation_metrics, accepted))
    accepted = bool(results) and sum(fold.accepted for fold in results) >= (len(results) + 1) // 2
    return WalkForwardReport(strategy.version, results, accepted)
