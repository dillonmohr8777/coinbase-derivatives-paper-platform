.PHONY: install lint fmt typecheck test run backtest radar

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

backtest:       ## backtest a strategy version over fixtures: make backtest STRAT=strategy_v1
	python -m app.eval.backtest $(STRAT)

radar:          ## run a whale-radar query: make radar Q="Find me whale trades..."
	python -m app.radar.cli "$(Q)"
