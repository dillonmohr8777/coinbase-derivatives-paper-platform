# Live Readiness Gate

Live trading is not implemented or enabled in v1. Promotion requires a separate approved
change after the paper evidence satisfies every item below.

## Required evidence

- At least 30 consecutive days of Coinbase public-data paper operation.
- Zero unexplained reconciliation differences between fills, positions, cash, and equity.
- Walk-forward results across trending, ranging, crash, and volatility-expansion regimes.
- Observed spread, slippage, fees, and funding are no better than the backtest assumptions.
- Daily loss, drawdown, leverage, concentration, stale-data, and liquidation tests pass.
- Restart recovery, duplicate-order prevention, API timeout, rate-limit, and disconnect drills pass.

## Separate live implementation requirements

- A dedicated Coinbase key with view and trade only; no transfer or withdrawal capability.
- Account, portfolio, product, region eligibility, increment, margin mode, and session verified.
- Manual arming plus two off-by-default configuration gates.
- Per-order notional cap, portfolio gross cap, reduce-only emergency exits, and mass cancel.
- Idempotent client order ids and startup reconciliation before any new order.
- Human-visible kill switch, automatic daily stop, and alerting for every rejection or mismatch.
- Canary phase at the smallest permitted notional, followed by explicit human review.

No profitability claim or backtest result can waive these requirements.
