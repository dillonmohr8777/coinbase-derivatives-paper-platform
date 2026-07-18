"""Shared domain types. Keep these stable — every module speaks in these."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Candle:
    symbol: str
    timeframe: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: Side
    size: float
    rationale: str
    strategy_version: str
    ts: datetime


@dataclass(frozen=True)
class Fill:
    symbol: str
    side: Side
    qty: float
    price: float        # includes modeled slippage
    fee: float
    ts: datetime
    paper: bool = True


@dataclass
class Metrics:
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_return: float = 0.0
    avg_win: float = 0.0
    trades: int = 0


# --- Whale radar ---
@dataclass
class AltSignal:
    """A single institutional/alt-data data point (options flow, dark pool, or filing)."""
    source: str                 # "options_flow" | "dark_pool" | "sec_filing"
    symbol: str
    ts: datetime
    detail: str                 # human-readable evidence
    magnitude: float            # normalized size/notional for scoring


@dataclass
class WhaleRow:
    symbol: str
    score: float
    signals: list[AltSignal] = field(default_factory=list)   # evidence trail / citations


@dataclass
class WhaleReport:
    query: str
    rows: list[WhaleRow] = field(default_factory=list)       # ranked, highest score first
