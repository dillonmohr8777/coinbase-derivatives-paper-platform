# Paper Operations

The local runner consumes Coinbase public perpetual-futures data and writes only simulated
trades, logs, and portfolio snapshots to `whale_desk.sqlite`.

```powershell
python -m app.paper_engine
python -m uvicorn app.dashboard:app --host 127.0.0.1 --port 8000
```

Default products are `BTC-PERP-INTX`, `ETH-PERP-INTX`, and `SOL-PERP-INTX`. Public product
discovery should be checked before each deployment because listings and availability change.

## Daily review

- Confirm the newest candles are current and no symbol is repeatedly halted.
- Compare equity, gross notional, maintenance margin, and liquidation buffer.
- Review fills for spread/slippage assumptions and partial execution.
- Record funding debits/credits and any adapter or rate-limit errors.
- Never change `TRADING_MODE=paper` or `ALLOW_LIVE_ORDERS=false` during this program.

The paper period begins only when the background runner is healthy on Coinbase public data.
