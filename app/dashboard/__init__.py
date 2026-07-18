"""FastAPI dashboard and offline-first API for the paper desk."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.data import get_provider
from app.eval import compute_metrics
from app.memory import LocalMemory
from app.radar import FixtureDarkPool, FixtureOptionsFlow, FixtureSecFilings, Radar
from config.settings import get_settings


class DashboardState:
    def __init__(self, memory: LocalMemory | None = None) -> None:
        self.memory = memory
        self.runlog = ["SYSTEM  Whale Desk ready — PAPER mode"]
        self.trades: list[dict[str, Any]] = []
        self.metrics = {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_return": 0.0,
            "avg_win": 0.0,
            "equity_curve": [10_000.0],
        }
        self.portfolio: dict[str, Any] = {
            "equity": 10_000.0,
            "gross_notional": 0.0,
            "liquidation_buffer": 10_000.0,
            "positions": {},
        }
        self.refresh()

    def refresh(self) -> None:
        if not self.memory:
            return
        self.trades = self.memory.list_kind("trade", 100)
        logs = self.memory.list_kind("runlog", 200)
        if logs:
            self.runlog = [str(item.get("message", "")) for item in reversed(logs)]
        outcomes = self.memory.list_kind("outcome", 500)
        pnls = [float(item.get("pnl", 0)) for item in outcomes]
        calculated = compute_metrics(pnls)
        self.metrics.update(asdict(calculated))
        snapshots = self.memory.list_kind("portfolio", 1)
        if snapshots:
            self.portfolio = snapshots[0]


class RadarRequest(BaseModel):
    query: str
    symbols: list[str] = ["AAPL", "MSFT", "NVDA", "TSLA", "COIN"]


HTML = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Whale Desk</title><style>
:root{color-scheme:dark;--bg:#07110f;--panel:#0d1c18;--line:#214138;--mint:#62f5bd;--muted:#8aa69d}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 80% 0,#153b30,var(--bg) 34%);color:#eefbf6;font:14px system-ui;padding:24px}header{display:flex;justify-content:space-between}.badge{color:#07110f;background:var(--mint);padding:7px 11px;border-radius:999px;font-weight:800}.metrics,.grid{display:grid;gap:14px}.metrics{grid-template-columns:repeat(4,1fr);margin:22px 0}.grid{grid-template-columns:1.4fr 1fr}.panel{background:#0d1c18dd;border:1px solid var(--line);border-radius:18px;padding:18px}.value{font-size:28px;font-weight:800;color:var(--mint)}#log{height:330px;overflow:auto;white-space:pre-wrap;font:13px ui-monospace;color:#b9f9df}.muted{color:var(--muted)}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid var(--line)}input{width:78%;background:#07110f;color:white;border:1px solid var(--line);padding:12px;border-radius:10px}button{padding:12px;border:0;border-radius:10px;background:var(--mint);font-weight:800}@media(max-width:800px){.metrics{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}</style></head><body>
<header><div><h1>Whale Desk</h1><div class='muted'>Derivatives research + institutional radar</div></div><div class='badge'>PAPER ONLY</div></header><section class='metrics'><div class='panel'><div class='muted'>WIN RATE</div><div class='value' id='win'>0%</div></div><div class='panel'><div class='muted'>PROFIT FACTOR</div><div class='value' id='pf'>0.00</div></div><div class='panel'><div class='muted'>TOTAL RETURN</div><div class='value' id='ret'>$0</div></div><div class='panel'><div class='muted'>AVG WIN</div><div class='value' id='avg'>$0</div></div></section>
<main class='grid'><section class='panel'><h2>Bot run log</h2><div id='log'></div></section><section class='panel'><h2>Recent trades</h2><table><thead><tr><th>Symbol</th><th>Action</th><th>Strategy</th></tr></thead><tbody id='trades'></tbody></table></section><section class='panel'><h2>Big Whale Trades</h2><input id='query' value='Find me whale trades where institutions are positioning before the move'><button onclick='scan()'>Scan</button><div id='radar'></div></section><section class='panel'><h2>Portfolio risk</h2><div class='value' id='equity'>$10,000</div><p>Gross notional: <span id='gross'>$0</span><br>Liquidation buffer: <span id='buffer'>$10,000</span></p><p class='muted'>Look-ahead blocked · costs modeled · daily stop · stale-data fail-safe. No live-money adapter.</p></section><section class='panel'><h2>BTC perpetual price</h2><canvas id='chart' width='900' height='260' style='width:100%;height:260px'></canvas></section></main>
<script>const runlog=document.querySelector('#log');new EventSource('/api/runlog').onmessage=e=>{runlog.textContent+=e.data+'\n';runlog.scrollTop=runlog.scrollHeight};fetch('/api/metrics').then(r=>r.json()).then(m=>{win.textContent=(m.win_rate*100).toFixed(1)+'%';pf.textContent=m.profit_factor.toFixed(2);ret.textContent='$'+m.total_return.toFixed(2);avg.textContent='$'+m.avg_win.toFixed(2)});fetch('/api/portfolio').then(r=>r.json()).then(p=>{equity.textContent='$'+p.equity.toFixed(2);gross.textContent='$'+p.gross_notional.toFixed(2);buffer.textContent='$'+p.liquidation_buffer.toFixed(2)});fetch('/api/trades').then(r=>r.json()).then(rows=>trades.innerHTML=rows.map(x=>`<tr><td>${x.symbol}</td><td>${x.action}</td><td>${x.strategy}</td></tr>`).join(''));fetch('/api/chart/BTC-PERP-INTX').then(r=>r.json()).then(x=>{let c=chart.getContext('2d'),v=x.candles.map(y=>y.close),lo=Math.min(...v),hi=Math.max(...v);c.strokeStyle='#62f5bd';c.lineWidth=3;c.beginPath();v.forEach((p,i)=>{let px=i/(v.length-1)*900,py=240-(p-lo)/(hi-lo||1)*220;i?c.lineTo(px,py):c.moveTo(px,py)});c.stroke()});async function scan(){let r=await fetch('/api/radar',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({query:query.value})});let x=await r.json();radar.innerHTML='<table>'+x.rows.map(y=>`<tr><td><b>${y.symbol}</b></td><td>${y.score.toFixed(1)}</td><td>${y.signals.map(s=>s.source).join(', ')}</td></tr>`).join('')+'</table>'}</script></body></html>"""


def create_app(state: DashboardState | None = None) -> FastAPI:
    state = state or DashboardState()
    app = FastAPI(title="Whale Desk", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return HTML

    @app.get("/api/trades")
    def trades() -> list[dict[str, Any]]:
        state.refresh()
        return state.trades[-100:]

    @app.get("/api/metrics")
    def metrics() -> dict[str, Any]:
        state.refresh()
        return state.metrics

    @app.get("/api/portfolio")
    def portfolio() -> dict[str, Any]:
        state.refresh()
        return state.portfolio

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
        report = Radar(
            [FixtureOptionsFlow(), FixtureDarkPool(), FixtureSecFilings()]
        ).find_whale_trades(request.query, request.symbols)
        state.runlog.append(f"RADAR  ranked {len(report.rows)} institutional setups")
        return asdict(report)

    @app.get("/api/chart/{symbol}")
    def chart(symbol: str) -> dict[str, Any]:
        candles = get_provider(get_settings().market_data_provider).get_candles(symbol, "5m", 120)
        return {"symbol": symbol, "candles": [asdict(c) for c in candles], "markers": []}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "trading_mode": "paper"}

    return app


app = create_app(DashboardState(LocalMemory()))
