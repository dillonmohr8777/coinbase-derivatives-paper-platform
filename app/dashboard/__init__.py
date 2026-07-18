"""Web dashboard (spec §3.7): run log, recent trades, metrics header + equity curve,
whale-radar panels + Final-results table, price chart with BUY/SELL markers.

v1: FastAPI + server-rendered + SSE for the live run log. A React front can come later; do not
block v1 on it.
"""
from __future__ import annotations

# TODO(codex): FastAPI app with:
#   GET  /                      -> dashboard page (run log, trades, metrics, radar view)
#   GET  /api/runlog (SSE)      -> stream orchestrator/agent log lines
#   GET  /api/trades            -> recent trades (Time, Symbol, Action, Strategy version)
#   GET  /api/metrics           -> win_rate, profit_factor, total_return, avg_win, equity curve
#   POST /api/radar {query}     -> WhaleReport rendered as panels + Final-results table
#   GET  /api/chart/{symbol}    -> candles + BUY/SELL markers
#
# Keep the source layout: terminal-style run log is the primary element.
