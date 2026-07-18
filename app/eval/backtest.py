"""Backtest a strategy version over fixtures. `make backtest STRAT=strategy_v1`.

No look-ahead: at each step the strategy only sees candles up to and including `i`.
"""

from __future__ import annotations

import sys

from app.data import get_provider
from app.eval import compute_metrics
from app.execution import PaperBroker
from app.strategy import get_strategy
from app.types import Side
from config.settings import get_settings, load_yaml_config


def run_backtest(version: str) -> None:
    cfg = load_yaml_config()
    get_settings()
    provider = get_provider("fixture")
    strat = get_strategy(version)
    broker = PaperBroker(cfg["execution"]["fee_bps"], cfg["execution"]["slippage_bps"])

    symbol = cfg["watchlist"]["equities"][0]
    candles = provider.get_candles(symbol, "1h", limit=200)

    pnls: list[float] = []
    entry = None
    for i in range(len(candles)):
        window = candles[: i + 1]  # only past+present -> no look-ahead
        for sig in strat.generate_signals(window, context={}):
            fill = broker.place_order(sig, window[-1].close)
            if sig.side is Side.BUY and entry is None:
                entry = fill.price + fill.fee
            elif sig.side is Side.SELL and entry is not None:
                pnls.append((fill.price - entry) - fill.fee)
                entry = None

    m = compute_metrics(pnls)
    print(f"\nBacktest {version} on {symbol} ({m.trades} trades)")
    print(f"  win_rate      {m.win_rate:.1%}")
    print(f"  profit_factor {m.profit_factor:.2f}")
    print(f"  total_return  {m.total_return:+.2f}")
    print(f"  avg_win       {m.avg_win:+.2f}")
    # NOTE: fixtures are synthetic — these numbers demonstrate the pipeline, not performance.


if __name__ == "__main__":
    run_backtest(sys.argv[1] if len(sys.argv) > 1 else "strategy_v1")
