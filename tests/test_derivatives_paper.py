from datetime import datetime, timezone

import pytest

from app.execution import DerivativesPaperBroker
from app.types import Side, Signal


def signal(side: Side, size: float = 1) -> Signal:
    return Signal("BTC-PERP-INTX", side, size, "test", "strategy_v2", datetime.now(timezone.utc))


def test_paper_portfolio_marks_funding_and_closes():
    broker = DerivativesPaperBroker(starting_equity=10_000, max_leverage=3)
    broker.place_order(signal(Side.BUY), 100, best_ask=100.1)
    broker.mark("BTC-PERP-INTX", 110)
    assert broker.equity > 10_000
    payment = broker.apply_funding("BTC-PERP-INTX", 0.001)
    assert payment > 0
    broker.place_order(signal(Side.SELL), 110, best_bid=109.9)
    assert not broker.positions and broker.cash > 10_000


def test_partial_fill_and_leverage_limit():
    broker = DerivativesPaperBroker(starting_equity=100, max_leverage=2)
    fill = broker.place_order(signal(Side.BUY, 2), 50, available_qty=0.5)
    assert fill.qty == 0.5
    with pytest.raises(RuntimeError, match="leverage"):
        broker.place_order(signal(Side.BUY, 10), 50)


def test_liquidation_halts_new_orders():
    broker = DerivativesPaperBroker(
        starting_equity=100, max_leverage=3, maintenance_margin_rate=0.1
    )
    broker.place_order(signal(Side.BUY, 2), 100)
    broker.mark("BTC-PERP-INTX", 50)
    assert broker.halted and not broker.positions
    with pytest.raises(RuntimeError, match="halted"):
        broker.place_order(signal(Side.BUY), 50)
