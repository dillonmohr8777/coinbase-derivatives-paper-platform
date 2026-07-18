# whale-desk (scaffold)

Starter skeleton for the AI trading bot + whale-trade radar. See `../01-product-spec.md` and
`../03-build-plan.md`. Grep for `TODO(codex)` for the work items.

The current build is deliberately paper-only. Start the CLI with `make run`, the dashboard
with `make dashboard`, the offline backtest with `make backtest STRAT=strategy_v1`, and the
fixture whale scan with `make radar Q="Find me whale trades"`.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/.env.example .env          # fill in later; fixtures work with no keys
make test                            # unit tests (no network)
make run                             # boots orchestrator in paper mode w/ fixtures
```

Defaults: `TRADING_MODE=paper`, fixture data + mock LLM, local SQLite memory. Nothing here
places a live order. See `../04-codex-kickoff-prompt.md` to start an agent on it.
