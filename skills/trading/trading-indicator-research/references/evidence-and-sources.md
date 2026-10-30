# Trading indicator evidence and sources

Canonical numbers and where they come from. Use to answer "which indicator is best" without relying on marketing.

## The benchmark study (primary source for "does anything beat buy-and-hold")
IndicatorEdge: 644,149 out-of-sample backtests, 382 indicators across 871 assets, costs included.
- Only **26% of indicator-asset combinations beat buy-and-hold**.
- Any **single** indicator beat buy-and-hold on only ~8–14% of assets.
- Median best Sharpe across assets was **0.62** — a real but modest edge.
- 571 of 903 assets (63%) had at least one indicator that cleared the bar — that is selection, not universal skill.
- Short-side signals added measurable edge in only 17.4% of cases.

### The win-rate trap table (high win rate, still loses)
| Indicator | Median win rate | Beat buy-and-hold on |
|---|---|---|
| Murrey Math Lines | 74.3% | 11% of assets |
| Holy Grail Confluence | 73.3% | 8% |
| Money Flow Index | 72.2% | 9% |
| RSI Mean-Reversion | 71.7% | 10% |
| CCI | 71.0% | 9% |
| Ultimate Oscillator | 72.7% | 11% |

### Best-per-asset-class leaders
- **Stocks**: Fibonacci Pivots (best on 22 assets), Projection Bands (16), Intraday Momentum Index (16), Camarilla Pivots (16), Markov Regime (14).
- **Forex**: Fisher Transform (17 pairs).
- **Crypto**: MA Envelope (5), Fibonacci Pivots and Delta Volume Rising (4 each).
- **Commodities**: Keltner Mean-Reversion (3).
- **ETFs**: QQE (4).

The site's own caveat, worth quoting: "Won most often is not 'wins on everything.'" The winner is asset-specific.

## The worked example: Connors RSI(2) mean reversion
The most re-tested retail indicator system. Use it as the template for how to present any indicator — rules, then numbers, then caveats.

**Rules (the classic long-only form)**
1. Filter: price above its 200-day SMA (buy dips in uptrends only).
2. Entry: buy at the close when RSI(2) closes below 10 (variants use 5, or 30 as a conservative band).
3. Exit: RSI(2) crosses back above 70 or 80, or price closes below the 200-day SMA.

**Published numbers (SPY, 1993 onward)**
- Buy RSI(2) < 10, sell > 80: **91% win rate**, +0.82% average per trade, 33% max drawdown, only 42% of time in market.
- On S&P 500 stocks with the 200-day filter: **75–79% win rate**.
- Depth gradient (average return over next 5 days, S&P 500 stocks above 200-day MA): RSI(2) < 2 → +0.92%; < 5 → +0.68%; < 10 → +0.48%; < 25 → +0.22%. The lower the reading the stronger the bounce — this gradient is the edge.
- Annual return ~9%, max drawdown 34%, time in market 28% (QuantifiedStrategies SPY 1993–present variant).

**Why RSI(2) and not RSI(14)**
RSI(14) smooths two weeks of price; RSI(2) reads only the last two days, so it spikes to extremes after a single bad day. One red day takes RSI(2) from 66.7 to 29.6 while RSI(14) barely moves. The extreme reading *is* the signal — short-term panic, which reverts.

**Academic check**
February 2026 empirical study (luppiter Group): 100 US equities, 11 sectors, up to 64 years (1962–2026), 5,174 trades.
- Daily 30/70 RSI: 79.4% win rate, +7.66% average return per trade, n=3,892.
- Weekly 20/80: 96.3% win rate, +244% average return — but only 82 trades with a 6.5-year average hold.
- All four variants produced statistically significant positive mean returns per trade (p < 10⁻¹³).
- **All four significantly underperformed buy-and-hold on an annualized basis** (paired t-test p < 10⁻²⁰), because capital sits idle between signals.
- Strongest in bear markets and high-volatility regimes.

**Caveats that must travel with the recommendation**
- Underperforms buy-and-hold annually; ~40% time in market.
- Authors flag their own survivorship bias (universe = companies still listed at study end) — treat figures as an upper bound.
- CXO Advisory's published critique of Connors' book: no data-snooping correction, no out-of-sample testing, no transaction costs, no subperiod testing, and the cited millions of "trades" overlap so heavily a real trader could not have taken them all.
- Independent re-tests since 2010 find the edge softer than the 1995–2007 window; holds better on broad index ETFs (SPY, QQQ) than individual stocks.
- Original rules carry no hard stop loss; one un-stopped loser can erase many small wins. Add one when handing over rules.
- Fails badly in downtrends — the 200-day filter is the load-bearing part.

## Other verified reference points
- **MACD alone < 50% win rate** (arXiv 2206.12282, Dow/Nasdaq/S&P 500, 2015–2021). MACD+RSI improved it to 0.84 / 0.86 / 0.78 respectively. MACD is not a standalone edge.
- **RSI(14) standard 30/70: ~53% win rate**, outperformed buy-and-hold by ~45% over 26 years in one large-sample test; lags in trends, frequent false signals without filters.
- **Moving average crossover literature**: Brock, Lakonishok & LeBaron (1992) made simple MA rules statistically respectable; the 200-day MA as a standalone timing rule tested poorly (~29% win rate) in at least one large test.
- **Trend filters help**: filtering to trade only when ADX > 25 improved win rate meaningfully in one large sample.

## Vendor / community script availability
- **TradingView community scripts**: free accounts see description + screenshot only; code requires a paid plan. Not citable as evidence.
- **GitHub is the readable source.** Topic pages `github.com/topics/pinescript` (~514 repos) and `.../pinescript-indicators` are the entry points.
- **Recommended starting repos** (verify the version tag before use — most target v4/v5):
  - `pAulseperformance/awesome-pinescript` — 1.9k stars, the master index. Start here.
  - `just-nilux/awesome-tradingview` — curated, includes alert/webhook scripts.
  - `everget/tradingview-pinescript-indicators` — classic indicators (EMA, RSI, MACD, Bollinger, ATR, Ichimoku, Supertrend).
  - `ArunKBhaskar/PineScript`, `pinecoders/pine-utils` (snippets/templates), `Alorse/pinescript-strategies` (50+ strategies), `harryguiacorn/TradingView-Proprietary-Indicators`, `razorbladekisses/Tradingview-Indicators` (v5).
  - `AkashSasikumar47/gainz-trading-indicators` — 35 indicators in v6, one `.pine` file each, good for reading clean v6.
  - `LuxAlgo/PineTS` — run Pine Script outside TradingView (Node/browser).
  - `PyneSys/pynecore` — same idea, Python.
- **Search trick**: on GitHub use `language:Pine Script bybit` or browse the topic pages.
- **Pine Script docs URL**: `tradingview.com/pine-script-docs/en/v6/index.html` 404s; the working entry point is `.../en/v5/index.html` (which now serves as the docs home and links Primer / Language / Concepts / Release notes). Do not build links on the v6 path.
- **Webhook/alert bots** (if asked how TradingView connects to an exchange or a messenger): `lth-elm/TradingView-Webhook-Trading-Bot` (Flask, places real exchange orders), `fabston/TradingView-Webhook-Bot` (routes alerts to Telegram/Discord/Slack).
