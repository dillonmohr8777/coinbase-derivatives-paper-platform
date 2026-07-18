"""CLI: run a whale-radar query. `make radar Q="Find me whale trades..."`"""
from __future__ import annotations

import sys

from app.radar import FixtureDarkPool, FixtureOptionsFlow, FixtureSecFilings, Radar
from config.settings import get_settings, load_yaml_config


def main(argv: list[str]) -> int:
    query = argv[1] if len(argv) > 1 else (
        "Find me whale trades where institutions are positioning before the move."
    )
    cfg = load_yaml_config()
    get_settings()  # loads env / validates gates
    symbols = cfg["watchlist"]["equities"] + [s.split("/")[0] for s in cfg["watchlist"]["crypto"]]

    radar = Radar(
        connectors=[FixtureOptionsFlow(), FixtureDarkPool(), FixtureSecFilings()],
        min_signals=cfg["radar"]["min_signals_to_rank"],
        window_hours=cfg["radar"]["correlation_window_hours"],
    )
    report = radar.find_whale_trades(query, symbols)

    print(f"\nQuery: {report.query}\n")
    print(f"{'RANK':<5}{'SYMBOL':<10}{'SCORE':<16}EVIDENCE")
    for i, row in enumerate(report.rows, 1):
        evidence = "; ".join(f"[{s.source}] {s.detail}" for s in row.signals)
        print(f"{i:<5}{row.symbol:<10}{row.score:<16,.0f}{evidence}")
    if not report.rows:
        print("(no tickers met the min-signals threshold)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
