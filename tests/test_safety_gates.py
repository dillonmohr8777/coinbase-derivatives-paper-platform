"""Safety-gate tests: v1 must never expose a live-order path by default."""
from app.execution import PaperBroker, get_broker
from config.settings import Settings


def test_default_settings_are_paper_only():
    s = Settings()
    assert s.trading_mode == "paper"
    assert s.allow_live_orders is False
    assert s.live_enabled is False


def test_get_broker_returns_paper_by_default():
    assert isinstance(get_broker(Settings()), PaperBroker)


def test_live_requires_both_gates():
    assert Settings(trading_mode="live", allow_live_orders=False).live_enabled is False
    assert Settings(trading_mode="paper", allow_live_orders=True).live_enabled is False
    assert Settings(trading_mode="live", allow_live_orders=True).live_enabled is True
