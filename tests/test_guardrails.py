"""Guardrail tests — 'why most bots fail'. These must stay green (spec §5)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.guardrails import (
    GuardrailError,
    check_risk_limits,
    liquidity_ok,
    model_costs,
    no_lookahead,
)
from app.types import Candle, Side, Signal


def _sig(size=1.0):
    return Signal("AAPL", Side.BUY, size, "test", "strategy_v1", datetime.now(timezone.utc))


def test_no_lookahead_rejects_future_candle():
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    future = [Candle("AAPL", "1h", t + timedelta(hours=1), 1, 1, 1, 1, 1)]
    with pytest.raises(GuardrailError):
        no_lookahead(future, t)


def test_model_costs_applies_fees_and_slippage():
    assert model_costs(10_000, fee_bps=10, slippage_bps=5) == pytest.approx(15.0)


def test_risk_limits_block_oversize_and_stops():
    with pytest.raises(GuardrailError):
        check_risk_limits(_sig(size=100), price=100, open_positions=0, day_pnl=0,
                          max_position_usd=1000, max_concurrent_positions=5,
                          daily_loss_stop_usd=500)
    with pytest.raises(GuardrailError):
        check_risk_limits(_sig(), price=1, open_positions=5, day_pnl=0,
                          max_position_usd=1000, max_concurrent_positions=5,
                          daily_loss_stop_usd=500)
    with pytest.raises(GuardrailError):
        check_risk_limits(_sig(), price=1, open_positions=0, day_pnl=-600,
                          max_position_usd=1000, max_concurrent_positions=5,
                          daily_loss_stop_usd=500)


def test_liquidity_filter_skips_low_volume():
    vols = [1000, 1100, 1200, 1300, 1400]
    assert liquidity_ok(vols, current_volume=1500, min_percentile=40) is True
    assert liquidity_ok(vols, current_volume=500, min_percentile=40) is False
