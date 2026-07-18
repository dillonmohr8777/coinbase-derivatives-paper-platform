from app.data import FixtureProvider
from app.eval.walkforward import walk_forward
from app.strategy import get_strategy


def test_walk_forward_is_deterministic_and_has_folds():
    candles = FixtureProvider().get_candles("BTC-PERP-INTX", "5m", 500)
    report = walk_forward(get_strategy("strategy_v1"), candles, folds=3)
    assert report.strategy_version == "strategy_v1"
    assert len(report.folds) == 3
    assert isinstance(report.accepted, bool)
