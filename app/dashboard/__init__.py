"""FastAPI dashboard and offline-first API for the paper desk."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.data import FixtureProvider
from app.radar import FixtureDarkPool, FixtureOptionsFlow, FixtureSecFilings, Radar


class DashboardState:
    def __init__(self) -> None:
        self.runlog = ["SYSTEM  Whale Desk ready — PAPER mode"]
        self.trades: list[dict[str, Any]] = []
        self.metrics = {"win_rate": 0.0, "profit_factor": 0.0, "total_return": 0.0,
                        "avg_win": 0.0, "equity_curve": [10_000.0]}


class RadarRequest(BaseModel):
    query: str
    symbols: list[str] = ["AAPL", "MSFT", "NVDA", "TSLA", "COIN"]


HTML = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Whale Desk</title><style>
:root{color-scheme:dark;--bg:#07110f;--panel:#0d1c18;--line:#214138;--mint:#62f5bd;--muted:#8aa69d}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 80% 0,#153b30,var(--bg) 34%);color:#eefbf6;font:14px system-ui;padding:24px}header{display:flex;justify-content:space-between}.badge{color:#07110f;background:var(--mint);padding:7px 11px;border-radius:999px;font-weight:800}.metrics,.grid{display:grid;gap:14px}.metrics{grid-template-columns:repeat(4,1fr);margin:22px 0}.grid{grid-template-columns:1.4fr 1fr}.panel{background:#0d1c18dd;border:1px solid var(--line);border-radius:18px;padding:18px}.value{font-size:28px;font-weight:800;color:var(--mint)}#log{height:330px;overflow:auto;white-space:pre-wrap;font:13px ui-monospace;color:#b9f9df}.muted{color:var(--muted)}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid var(--line)}input{width:78%;background:#07110f;color:white;border:1px solid var(--line);padding:12px;border-radius:10px}button{padding:12px;border:0;border-radius:10px;background:var(--mint);font-weight:800}@media(max-width:800px){.metrics{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}</style></head><body>
<header><div><h1>Whale Desk</h1><div class='muted'>Derivatives research + institutional radar</div></div><div class='badge'>PAPER ONLY</div></header><section class='metrics'><div class='panel'><div class='muted'>WIN RATE</div><div class='value' id='win'>0%</div></div><div class='panel'><div class='muted'>PROFIT FACTOR</div><div class='value' id='pf'>0.00</div></div><div class='panel'><div class='muted'>TOTAL RETURN</div><div class='value' id='ret'>$0</div></div><div class='panel'><div class='muted'>AVG WIN</div><div class='value' id='avg'>$0</div></div></section>
<main class='grid'><section class='panel'><h2>Bot run log</h2><div id='log'></div></section><section class='panel'><h2>Recent trades</h2><table><thead><tr><th>Symbol</th><th>Action</th><th>Strategy</th></tr></thead><tbody id='trades'></tbody></table></section><section class='panel'><h2>Big Whale Trades</h2><input id='query' value='Find me whale trades where institutions are positioning before the move'><button onclick='scan()'>Scan</button><div id='radar'></div></section><section class='panel'><h2>Risk controls</h2><p>Look-ahead blocked · costs modeled · position limits · daily stop · stale-data fail-safe · validation gate</p><p class='muted'>No live-money order adapter is enabled in v1.</p></section></main>
<script>const runlog=document.querySelector('#log');new EventSource('/api/runlog').onmessage=e=>{runlog.textContent+=e.data+'\n';runlog.scrollTop=runlog.scrollHeight};fetch('/api/metrics').then(r=>r.json()).then(m=>{win.textContent=(m.win_rate*100).toFixed(1)+'%';pf.textContent=m.profit_factor.toFixed(2);ret.textContent='$'+m.total_return.toFixed(2);avg.textContent='$'+m.avg_win.toFixed(2)});fetch('/api/trades').then(r=>r.json()).then(rows=>trades.innerHTML=rows.map(x=>`<tr><td>${x.symbol}</td><td>${x.action}</td><td>${x.strategy}</td></tr>`).join(''));async function scan(){let r=await fetch('/api/radar',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({query:query.value})});let x=await r.json();radar.innerHTML='<table>'+x.rows.map(y=>`<tr><td><b>${y.symbol}</b></td><td>${y.score.toFixed(1)}</td><td>${y.signals.map(s=>s.source).join(', ')}</td></tr>`).join('')+'</table>'}</script></body></html>"""


def create_app(state: DashboardState | None = None) -> FastAPI:
    state = state or DashboardState()
    app = FastAPI(title="Whale Desk", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return HTML

    @app.get("/api/trades")
    def trades() -> list[dict[str, Any]]:
        return state.trades[-100:]

    @app.get("/api/metrics")
    def metrics() -> dict[str, Any]:
        return state.metrics

    @app.get("/api/runlog")
    async def runlog() -> StreamingResponse:
        async def events():
            cursor = 0
            while True:
                while cursor < len(state.runlog):
                    yield f"data: {state.runlog[cursor]}\n\n"
                    cursor += 1
                await asyncio.sleep(1)
        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post("/api/radar")
    def radar(request: RadarRequest) -> dict[str, Any]:
        report = Radar([FixtureOptionsFlow(), FixtureDarkPool(), FixtureSecFilings()]).find_whale_trades(request.query, request.symbols)
        state.runlog.append(f"RADAR  ranked {len(report.rows)} institutional setups")
        return asdict(report)

    @app.get("/api/chart/{symbol}")
    def chart(symbol: str) -> dict[str, Any]:
        candles = FixtureProvider().get_candles(symbol, "5m", 120)
        return {"symbol": symbol, "candles": [asdict(c) for c in candles], "markers": []}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "trading_mode": "paper"}

    return app


app = create_app()
