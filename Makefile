.PHONY: install lint fmt typecheck test run paper dashboard backtest radar

install:
	pip install -r requirements.txt

lint:
	ruff check app tests

fmt:
	black app tests
	ruff check --fix app tests

typecheck:
	mypy app

test:
	pytest

run:            ## boot orchestrator in paper mode with fixtures
	python -m app.main

dashboard:      ## start the paper dashboard at http://127.0.0.1:8000
	python -m uvicorn app.dashboard:app --host 127.0.0.1 --port 8000

paper:          ## continuous paper-only derivatives loop
	python -m app.paper_engine

backtest:       ## backtest a strategy version over fixtures: make backtest STRAT=strategy_v1
	python -m app.eval.backtest $(STRAT)

radar:          ## run a whale-radar query: make radar Q="Find me whale trades..."
	python -m app.radar.cli "$(Q)"
