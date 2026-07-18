"""Common strategy interface. Every version implements generate_signals()."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.types import Candle, Signal


class Strategy(ABC):
    version: str = "base"

    @abstractmethod
    def generate_signals(self, candles: list[Candle], context: dict) -> list[Signal]:
        """Given past candles (only past — no look-ahead) return zero or more signals.

        `context` may include memory/lessons and current positions. Implementations MUST NOT
        peek at candles at/after the decision timestamp (see app.guardrails.no_lookahead).
        """
        raise NotImplementedError
