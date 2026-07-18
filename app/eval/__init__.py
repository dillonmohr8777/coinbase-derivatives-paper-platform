"""Evaluation: shared metrics used by backtest, paper, and (future) live."""

from __future__ import annotations

from app.types import Metrics


def compute_metrics(pnls: list[float]) -> Metrics:
    """Given per-trade PnL, compute the source video's headline metrics.

    win_rate, profit_factor, total_return, avg_win. Costs must already be baked into `pnls`.
    """
    if not pnls:
        return Metrics()
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return Metrics(
        win_rate=len(wins) / len(pnls),
        profit_factor=(gross_win / gross_loss) if gross_loss else float("inf"),
        total_return=sum(pnls),
        avg_win=(gross_win / len(wins)) if wins else 0.0,
        trades=len(pnls),
    )
