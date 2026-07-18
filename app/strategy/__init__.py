"""Versioned strategies. Register each version; the active one is chosen by config."""
from __future__ import annotations

from app.strategy.base import Strategy
from app.strategy.strategy_v1 import StrategyV1

_REGISTRY: dict[str, type[Strategy]] = {
    "strategy_v1": StrategyV1,
}


def get_strategy(version: str) -> Strategy:
    if version not in _REGISTRY:
        raise KeyError(f"unknown strategy version: {version}")
    return _REGISTRY[version]()


def register(version: str, cls: type[Strategy]) -> None:
    """Used when the agent authors a new versioned strategy (spec §3.2, M2)."""
    _REGISTRY[version] = cls
