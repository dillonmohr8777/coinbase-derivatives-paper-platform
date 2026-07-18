"""Execution: PAPER broker + cost model. Live path is gated off in v1 (spec §3.6)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.guardrails import model_costs
from app.types import Fill, PaperPosition, Side, Signal


class Broker(Protocol):
    def place_order(self, signal: Signal, price: float) -> Fill: ...


class PaperBroker:
    """Simulated fills with modeled fees + slippage. Never touches real money."""

    def __init__(self, fee_bps: float = 10, slippage_bps: float = 5) -> None:
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps

    def place_order(self, signal: Signal, price: float) -> Fill:
        notional = signal.size * price
        cost = model_costs(notional, self.fee_bps, self.slippage_bps)
        slip = price * self.slippage_bps / 10_000.0
        fill_price = price + slip if signal.side.value == "BUY" else price - slip
        return Fill(
            symbol=signal.symbol,
            side=signal.side,
            qty=signal.size,
            price=fill_price,
            fee=cost,
            ts=datetime.now(timezone.utc),
            paper=True,
        )


class DerivativesPaperBroker(PaperBroker):
    """Stateful cross-margin simulator for perpetual-futures paper trading.

    Models spread-aware fills, slippage, fees, partial liquidity, funding, leverage, margin,
    mark-to-market PnL, and liquidation. It has no network or live-order capability.
    """

    def __init__(
        self,
        starting_equity: float = 10_000,
        fee_bps: float = 3,
        slippage_bps: float = 2,
        max_leverage: float = 3,
        maintenance_margin_rate: float = 0.08,
    ) -> None:
        super().__init__(fee_bps, slippage_bps)
        self.cash = starting_equity
        self.starting_equity = starting_equity
        self.max_leverage = max_leverage
        self.maintenance_margin_rate = maintenance_margin_rate
        self.positions: dict[str, PaperPosition] = {}
        self.fills: list[Fill] = []
        self.halted = False

    @property
    def equity(self) -> float:
        return self.cash + sum(position.unrealized_pnl for position in self.positions.values())

    @property
    def gross_notional(self) -> float:
        return sum(position.notional for position in self.positions.values())

    @property
    def maintenance_margin(self) -> float:
        return self.gross_notional * self.maintenance_margin_rate

    @property
    def liquidation_buffer(self) -> float:
        return self.equity - self.maintenance_margin

    def place_order(
        self,
        signal: Signal,
        price: float,
        *,
        best_bid: float | None = None,
        best_ask: float | None = None,
        available_qty: float | None = None,
    ) -> Fill:
        if self.halted:
            raise RuntimeError("paper portfolio halted after liquidation or risk breach")
        qty = min(signal.size, available_qty) if available_qty is not None else signal.size
        if qty <= 0:
            raise ValueError("order has no executable quantity")
        market_price = (best_ask or price) if signal.side is Side.BUY else (best_bid or price)
        projected = self.gross_notional + qty * market_price
        if projected > max(self.equity, 0) * self.max_leverage:
            raise RuntimeError("paper order exceeds maximum gross leverage")
        partial = Signal(
            signal.symbol, signal.side, qty, signal.rationale, signal.strategy_version, signal.ts
        )
        fill = super().place_order(partial, market_price)
        self.cash -= fill.fee
        signed_qty = qty if signal.side is Side.BUY else -qty
        current = self.positions.get(signal.symbol)
        if current is None:
            self.positions[signal.symbol] = PaperPosition(
                signal.symbol,
                signed_qty,
                fill.price,
                fill.price,
                self.max_leverage,
            )
        else:
            old_qty = current.qty
            new_qty = old_qty + signed_qty
            if old_qty * signed_qty > 0:
                current.entry_price = (
                    current.entry_price * abs(old_qty) + fill.price * abs(signed_qty)
                ) / abs(new_qty)
            else:
                closed = min(abs(old_qty), abs(signed_qty))
                direction = 1 if old_qty > 0 else -1
                realized = closed * (fill.price - current.entry_price) * direction
                self.cash += realized
                current.realized_pnl += realized
                if new_qty and old_qty * new_qty < 0:
                    current.entry_price = fill.price
            current.qty = new_qty
            current.mark_price = fill.price
            if abs(new_qty) < 1e-12:
                del self.positions[signal.symbol]
        self.fills.append(fill)
        self._liquidate_if_needed()
        return fill

    def mark(self, symbol: str, mark_price: float) -> None:
        if symbol in self.positions:
            self.positions[symbol].mark_price = mark_price
        self._liquidate_if_needed()

    def apply_funding(self, symbol: str, funding_rate: float) -> float:
        position = self.positions.get(symbol)
        if not position:
            return 0.0
        # Positive funding: longs pay shorts. Negative funding reverses the transfer.
        payment = position.qty * position.mark_price * funding_rate
        self.cash -= payment
        position.funding_paid += payment
        self._liquidate_if_needed()
        return payment

    def snapshot(self) -> dict:
        return {
            "cash": self.cash,
            "equity": self.equity,
            "gross_notional": self.gross_notional,
            "maintenance_margin": self.maintenance_margin,
            "liquidation_buffer": self.liquidation_buffer,
            "halted": self.halted,
            "positions": {
                symbol: {
                    "qty": position.qty,
                    "entry_price": position.entry_price,
                    "mark_price": position.mark_price,
                    "unrealized_pnl": position.unrealized_pnl,
                    "funding_paid": position.funding_paid,
                }
                for symbol, position in self.positions.items()
            },
        }

    def _liquidate_if_needed(self) -> None:
        if self.positions and self.equity <= self.maintenance_margin:
            penalty = self.gross_notional * 0.005
            for position in self.positions.values():
                self.cash += position.unrealized_pnl
            self.cash -= penalty
            self.positions.clear()
            self.halted = True


def get_broker(settings) -> Broker:
    if settings.live_enabled:
        # TODO(codex): a real live broker MAY live here but stays UNREACHABLE in v1.
        # Do not implement/enable it. Fail loudly so it can't ship by accident.
        raise RuntimeError("live trading is out of scope for v1 — keep TRADING_MODE=paper")
    return PaperBroker()
