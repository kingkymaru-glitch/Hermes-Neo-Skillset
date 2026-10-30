---
name: crypto-trading-bot
description: Build/run MARU's Bybit SOL/USDT trading bot.
metadata:
  hermes:
    tags: [crypto, bybit, trading-bot, backtest, flask, websocket]
    related_skills: [trading-indicator-research, grounded-citations]
---

# Crypto Trading Bot (Bybit) — MARU's project

## Scope note
This skill is **bot-building**: MARU's Python engine at `~/Desktop/crypto_bot`, which pulls Bybit directly and contains no Pine Script and no TradingView dependency. When he asks about TradingView indicators, Pine Script code, or which indicator/strategy is best, that is a **research question** — use `trading-indicator-research` instead. The two overlap only on backtest methodology (survivorship bias, curve fitting, walk-forward validation).

Desktop project at `~/Desktop/crypto_bot`. SOL/USDT on Bybit. Two layers:
- **Research/backtest pipeline**: `data_layer.py` → `indicators.py` → `signals.py` → `backtest.py` → `plot_results.py` (4h + parallel 1h). Mean-reversion + momentum-breakout families (NOT unified).
- **Live engines**: `live_sandbox_1h.py`, `live_sandbox_15m.py` (raw `requests` to Bybit v5 REST, paper-only) and `live_1m/` (full real-time dashboard — current focus).

## CRITICAL: GO-LIVE safety gating (apply to ANY trading bot here)
Default = **SIMULATED** (live market data, NO real orders). Real orders only when ALL:
1. API keys in `.env` (`BYBIT_API_KEY` / `BYBIT_API_SECRET`)
2. Runtime arm via explicit confirm (e.g. `POST /api/arm` with `confirm=true`)
3. Kill switch OFF

Plus hard limits: max % capital/trade, daily loss limit auto-kill, visible KILL button. Never place real orders without this gate. Reference impl: `live_1m/engine.py`.

## Bybit v5 WebSocket live data
- URL: `wss://stream.bybit.com/v5/public/spot`
- Subscribe: `kline.1.SOLUSDT`, `orderbook.50.SOLUSDT`, `publicTrade.SOLUSDT`
- Order book: snapshot (`type=snapshot`) then deltas (`type=delta`); maintain bid/ask dicts, zero-qty = remove.
- Strategy: evaluate on **second-to-last closed candle**, execute at next open (no look-ahead).
- **MUST apply DNS fix before any Bybit call from this Mac** — see `references/bybit_dns_fix.md`.

## Dashboard stack (no build step)
Flask + Flask-SocketIO → `socketio.emit("update", …)` ~1.5s. Browser: TradingView `lightweight-charts` (CDN) for candles + BB/SMA overlays; `<canvas>` depth; buy/sell power = book imbalance + taker pressure. Single HTML template via `render_template_string`.

## Launcher preference (MARU)
Ship apps as Desktop double-click `.command` mirroring his `launch.command` (Luna-EDGE):
`pkill` prior → `nohup python3 app.py > log 2>&1 &` → `curl` port-wait loop → `open http://localhost:PORT`.
- MUST `export PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages"` — GUI `open` lacks user site-packages → `flask` import fails silently ("nothing happened").
- Make it **non-intrusive**: no lingering Terminal window after launch.

## Gotchas
- Bybit DNS sinkhole — see `references/bybit_dns_fix.md`. Non-negotiable here.
- Old `data_layer.py` CCXT hostname bug: `bytick.com` invalid → must be `bybit.com`.
- 1m indicators need warm-up candles; size SMA to keep warm-up short (SMA-30/14 ≈ 30 min vs SMA-200 ≈ 3.3h).
- Live WS pauses if Mac sleeps; resumes on wake (fine for tests, not always-on).
