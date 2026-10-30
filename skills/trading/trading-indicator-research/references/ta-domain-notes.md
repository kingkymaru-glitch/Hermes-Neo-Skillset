# Technical analysis domain notes

Plain-language explanations of the indicators that come up. MARU is not an engineer — explain the mechanism with an analogy, not a formula.

## RSI — Relative Strength Index
0–100 measure of how hard price has been rising vs falling recently. Below 30 traditionally "oversold", above 70 "overbought".
Analogy: a speedometer for buying pressure. A high reading means everyone who was going to buy already has.
- **RSI(14)** = standard, smooths two weeks. Good for trend confirmation, lags on quick moves.
- **RSI(2)** = last two days only. Reacts violently — one red day can take it from ~67 to ~30. Used for short-term mean reversion: buy the panic flush, sell when it normalises.
- **Mean reversion** = the bet that an extreme short-term move is overdone and will snap back. Works in ranges, fails badly in trends.

## Moving averages and the 200-day filter
- **SMA / EMA / RMA / WMA / HMA / VWMA / ALMA** — different ways of averaging price. SMA is flat, EMA weights recent bars more (reacts faster), HMA is designed to reduce lag.
- **200-day SMA as a regime gate** — "only take long signals while price is above it". The load-bearing rule in most mean-reversion systems: it stops you buying falling knives. Connors' data showed the filter's real contribution is cutting the worst drawdown, not creating the profit.
- **Crossover systems** (e.g. 50/200 "golden cross") — lagging by construction; the literature shows simple MA rules can be statistically respectable but are not a free lunch.
- **VWAP** — volume-weighted average price, resets daily. Anchor for intraday fair value.

## Momentum / oscillator family
- **MACD (12,26,9)** — difference of two EMAs plus a signal line. Crossover signals. Inherently lagging; alone it tests below 50% win rate.
- **Stochastic / Stochastic RSI** — where price sits in its recent range. Good in ranges, many false signals in trends.
- **CCI** — deviation from a statistical average, not bounded. High win rates in backtests, weak edge after buy-and-hold.
- **Williams %R, Ultimate Oscillator, Money Flow Index, Awesome Oscillator** — oscillator variants; several appear in the win-rate-trap table (high win rate, low beat rate).
- **ADX** — measures trend *strength*, not direction. Filtering entries to ADX > 25 is one of the more consistently useful refinements.

## Volatility / band family
- **Bollinger Bands** — moving average ± standard deviations. Band-touch alone is not a signal; needs volume or RSI confirmation. Squeeze = low volatility, often precedes a breakout.
- **ATR** — average true range. The building block for position sizing and stop distances. Use it to size, not to signal.
- **Keltner Channels** — band around an EMA using ATR instead of standard deviation. Leads for commodities in one large dataset.
- **Supertrend** — ATR-based trailing band that flips direction. Popular, but trend-following: it gives back in chop.

## Volume / order flow family
- **OBV (On-Balance Volume)** — cumulative volume signed by price direction. Confirms trends; weak in low-volume names.
- **Volume Profile / Delta Volume / CVD** — where volume traded by price level. Useful for locating support/resistance; the "best" indicator in some retail surveys, but level identification is not the same as a trade signal.
- **VWAP deviation bands, buy/sell power (book imbalance + taker pressure)** — microstructure reads; short-horizon only.

## Levels and "smart money" family
- **Fibonacci Pivots, Camarilla Pivots, Projection Bands** — derived support/resistance levels. Ranked highest on individual stocks in the large out-of-sample dataset. Note: level indicators identify *where*, not *when*.
- **SMC / ICT (order blocks, fair value gaps, liquidity sweeps)** — heavily promoted, and the large out-of-sample dataset found **zero** assets where SMC indicators beat buy-and-hold. Treat the category's marketing claims with strong scepticism.
- **Murrey Math Lines, Holy Grail Confluence** — appear in the win-rate-trap table: high win rate, low beat rate.
- **Candlestick pattern scripts** — pattern libraries exist but pattern recognition alone has weak standalone edge; they are confirmation tools.

## Regime detection
- **Markov Regime, ADX-based filters, VIX-regime filters** — the idea that indicator performance depends on the market state. This is the most defensible refinement axis: same signal, only in the regime where it historically worked.
- Markets trend roughly 30% of the time, so trend-following indicators are structurally out of the game most of the time.

## The recurring mechanics to explain when asked
- **Backtest-to-live gap** — survivorship bias, look-ahead bias, overfitting. Three separate systematic distortions; naming them is the fastest way to deflate an impressive-looking result.
- **Curve fitting** — tuning parameters until history looks perfect. The tell is a strategy that works on one asset or one date range and nowhere else.
- **Position sizing vs edge** — a small edge with oversized risk is a losing strategy. Risk control is part of the system, not an add-on.
- **Expectancy** = (win% × avg win) − (loss% × avg loss), in R. The number that matters; win rate alone hides the second half of the equation.
