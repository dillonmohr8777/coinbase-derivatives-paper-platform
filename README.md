# whale-desk (scaffold)

Starter skeleton for the AI trading bot + whale-trade radar. See `../01-product-spec.md` and
`../03-build-plan.md`. Grep for `TODO(codex)` for the work items.

The current build is deliberately paper-only. Start the CLI with `make run`, the dashboard
with `make dashboard`, the offline backtest with `make backtest STRAT=strategy_v1`, and the
fixture whale scan with `make radar Q="Find me whale trades"`.

For the Coinbase derivatives program, set `MARKET_DATA_PROVIDER=coinbase_public` and run
`make paper`. This reads public perpetual prices and writes simulated positions only. See
`OPERATIONS.md` for the daily review and `LIVE-READINESS.md` for the mandatory promotion gate.

The complete Actions workflow is staged at `ci/whale-desk-ci.yml`. Copy it into
`.github/workflows/` after the publishing credential has GitHub's `workflow` scope.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/.env.example .env          # fill in later; fixtures work with no keys
make test                            # unit tests (no network)
make run                             # boots orchestrator in paper mode w/ fixtures
```

Defaults: `TRADING_MODE=paper`, fixture data + mock LLM, local SQLite memory. Nothing here
places a live order. See `../04-codex-kickoff-prompt.md` to start an agent on it.
