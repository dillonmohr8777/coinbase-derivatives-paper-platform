"""Strategy + metrics tests (no network)."""
from app.data import FixtureProvider
from app.eval import compute_metrics
from app.strategy import get_strategy
from app.types import Signal


def test_strategy_v1_produces_valid_signals():
    candles = FixtureProvider().get_candles("AAPL", "1h", limit=200)
    signals = get_strategy("strategy_v1").generate_signals(candles, context={})
    assert all(isinstance(s, Signal) for s in signals)
    for s in signals:
        assert s.strategy_version == "strategy_v1"
        assert s.size > 0


def test_compute_metrics_headline_numbers():
    m = compute_metrics([100.0, -50.0, 200.0, -25.0])
    assert m.trades == 4
    assert m.win_rate == 0.5
    assert m.total_return == 225.0
    assert m.avg_win == 150.0
    assert m.profit_factor == (300.0 / 75.0)


def test_compute_metrics_empty():
    m = compute_metrics([])
    assert m.trades == 0 and m.total_return == 0.0
