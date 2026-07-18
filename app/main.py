"""Entrypoint: boot the orchestrator in PAPER mode with fixtures. `make run`.

This is intentionally a minimal, runnable slice (M1-ish): it loads candles for the whole
watchlist, runs the active strategy, paper-fills signals, and prints a run log that mirrors the
source video's first lines. Codex expands this into the full loop + dashboard (M2-M5).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.data import get_provider
from app.execution import get_broker
from app.memory import get_memory
from app.strategy import get_strategy
from config.settings import get_settings, load_yaml_config


def _log(msg: str) -> str:
    line = f"{datetime.now(timezone.utc):%I:%M:%S %p}  {msg}"
    print(line)
    return line


def main() -> None:
    settings = get_settings()
    cfg = load_yaml_config()

    if settings.live_enabled:
        raise SystemExit("Refusing to start: live trading is out of scope for v1.")

    provider = get_provider(settings.market_data_provider)
    broker = get_broker(settings)
    memory = get_memory(settings)
    strat = get_strategy(cfg["strategy"]["active"])

    symbols = cfg["watchlist"]["equities"] + cfg["watchlist"]["crypto"]
    _log(f"Trade history loaded for {', '.join(symbols)}.")
    _log(f"Mode={settings.trading_mode} | strategy={strat.version} | provider={settings.market_data_provider}")

    for symbol in symbols:
        candles = provider.get_candles(symbol, cfg["timeframes"][-2], limit=200)
        prior = memory.search(symbol, limit=3)
        if prior:
            _log(f"{symbol}: recalled {len(prior)} prior lesson(s) from memory.")
        signals = strat.generate_signals(candles, context={"memory": prior})
        if not signals:
            _log(f"{symbol}: no signal (or filtered by low-volume/guardrails).")
            continue
        for sig in signals:
            fill = broker.place_order(sig, candles[-1].close)
            _log(f"{strat.version.upper()} SIGNAL: {sig.side.value} {symbol} -> EXECUTING ORDER "
                 f"(paper) @ {fill.price:.2f} fee {fill.fee:.2f}")
            memory.write("trade", {
                "symbol": symbol, "side": sig.side.value, "price": fill.price,
                "strategy": sig.strategy_version, "rationale": sig.rationale,
            })

    _log("Run complete (paper).")


if __name__ == "__main__":
    main()
