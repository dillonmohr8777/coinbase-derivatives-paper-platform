# whale-desk (scaffold)

Starter skeleton for the AI trading bot + whale-trade radar. See `../01-product-spec.md` and
`../03-build-plan.md`. Grep for `TODO(codex)` for the work items.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/.env.example .env          # fill in later; fixtures work with no keys
make test                            # unit tests (no network)
make run                             # boots orchestrator in paper mode w/ fixtures
```

Defaults: `TRADING_MODE=paper`, fixture data + mock LLM, local SQLite memory. Nothing here
places a live order. See `../04-codex-kickoff-prompt.md` to start an agent on it.
