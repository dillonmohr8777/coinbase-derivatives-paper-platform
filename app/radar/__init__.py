"""Whale-trade radar (Source B): options flow + dark pool + SEC filings -> ranked report.

Prompt: 'Find me whale trades where institutions are positioning before the move.'
Each connector has a fixture impl so the sample prompt works with zero paid keys.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import log1p
from typing import Protocol

from app.types import AltSignal, WhaleReport, WhaleRow


class AltDataConnector(Protocol):
    def fetch(self, symbols: list[str]) -> list[AltSignal]: ...


class FixtureOptionsFlow:
    def fetch(self, symbols: list[str]) -> list[AltSignal]:
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        # Deterministic sample: unusual call sweep on the first two symbols.
        return [
            AltSignal("options_flow", s, now, f"unusual call sweep on {s} (>$1M premium)", 1_200_000)
            for s in symbols[:2]
        ]


class FixtureDarkPool:
    def fetch(self, symbols: list[str]) -> list[AltSignal]:
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        return [
            AltSignal("dark_pool", s, now, f"large dark-pool print on {s} (block > 500k sh)", 5_000_000)
            for s in symbols[:2]
        ]


class FixtureSecFilings:
    def fetch(self, symbols: list[str]) -> list[AltSignal]:
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        return [
            AltSignal("sec_filing", symbols[0], now, f"Form 4 insider buy filed for {symbols[0]}", 800_000)
        ]


# TODO(codex): real connectors — options flow / dark pool (Unusual Whales, Polygon) and SEC
#              EDGAR (free; requires a User-Agent). Rate-limit + cache. Select via settings.


class Radar:
    def __init__(self, connectors: list[AltDataConnector], min_signals: int = 2,
                 window_hours: int = 48) -> None:
        self.connectors = connectors
        self.min_signals = min_signals
        self.window_hours = window_hours

    def find_whale_trades(self, query: str, symbols: list[str]) -> WhaleReport:
        signals: list[AltSignal] = []
        for c in self.connectors:
            signals.extend(c.fetch(symbols))

        # Correlate by ticker; a ticker "ranks" only with >= min_signals distinct sources.
        by_symbol: dict[str, list[AltSignal]] = {}
        for s in signals:
            by_symbol.setdefault(s.symbol, []).append(s)

        rows: list[WhaleRow] = []
        for sym, sigs in by_symbol.items():
            newest = max(s.ts for s in sigs)
            sigs = [
                s for s in sigs
                if abs((newest - s.ts).total_seconds()) <= self.window_hours * 3600
            ]
            sources = {s.source for s in sigs}
            if len(sources) < self.min_signals:
                continue
            score = sum(log1p(max(s.magnitude, 0)) for s in sigs) * len(sources)
            rows.append(WhaleRow(symbol=sym, score=score, signals=sigs))

        rows.sort(key=lambda r: r.score, reverse=True)
        return WhaleReport(query=query, rows=rows)
