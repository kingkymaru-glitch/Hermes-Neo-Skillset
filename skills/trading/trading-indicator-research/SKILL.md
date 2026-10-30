---
name: trading-indicator-research
description: Use when asked which trading indicator is best.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, technical-analysis, pine-script, research, evidence]
    related_skills: [crypto-trading-bot, grounded-citations]
---

# Trading Indicator & Strategy Research

## When to Use
- Asked which indicator/strategy/script is "best", "most accurate", or has the "highest success rate" — any market (stocks, crypto, forex, commodities).
- Asked to evaluate a specific indicator, Pine Script repo, or published backtest claim.
- Asked where to find open-source indicator code (TradingView scripts vs GitHub).
- Before recommending any trading script to MARU as evidence rather than a sales pitch.

The question usually arrives with a false premise baked in. Correct it in the first paragraph, before giving any number.

## The premise check (do this first)
These questions are almost always marketing-shaped. Name the trap explicitly before answering:

- **"Best success rate" / "most accurate indicator"** — an indicator has no win rate. Win rate belongs to a complete rule set: entry, exit, stop, position size, market, timeframe, date range. Changing any one changes the number. Quote this framing back rather than supplying a headline figure.
- **High win rate ≠ profit.** Mean-reversion and "oversold bounce" setups collect many small wins and occasionally eat one large loss, and sit in cash while the asset trends up without them. Green ticks, red P&L.
- **The risk:reward tell.** A script advertising a very high win rate will pair it with a 5:1 or 10:1 risk:reward ratio. That is not accuracy, it is a trade-off — it wins small often and loses big rarely. Point this out whenever you see it.

## The verification stack (what actually answers the question)
Run these in order. Each step replaces an opinion with a source.

1. **Out-of-sample benchmark study** — the primary source for "what beats buy-and-hold, on what fraction of assets". See `references/evidence-and-sources.md` for the canonical numbers (IndicatorEdge 644,149 backtests / 382 indicators / 871 assets; the 26% beat rate; the win-rate-trap table).
2. **Peer-reviewed empirical study** — for a single indicator's statistical significance, mean return per trade, and trade count. Prefer studies that report *average return per trade* and *p-values*, not just a win rate.
3. **Methodological critique** — find the published criticism of the source you are about to recommend. CXO Advisory's critique of Connors' work is the model here. A source that has not been critiqued is not yet evidence.
4. **Vendor/community scripts as illustration only** — never as the basis of a recommendation. See the code-access caveat below.

Then deliver: the one system with the most evidence, its exact rules, its real numbers, and the caveats — in that order. See `references/evidence-and-sources.md` for the worked Connors RSI(2) case (the standard example of doing this right) and `references/ta-domain-notes.md` for plain-language explanations of the indicators involved.

## Getting real price data (the part that costs time)

**Yahoo Finance rate-limits aggressively.** `query1.finance.yahoo.com` returns 429 within a handful of requests from one IP, and it is IP-level, so cookies and crumbs do not help. Two ways through:

1. **Real browser, in-page fetch** — the method that works. Navigate to any `query1.finance.yahoo.com` URL to establish the origin, then use `browser_exec`'s `js()` with an in-page `fetch()` (same-origin, no CORS). Have the JS build CSV text and return it, and write the files from Python so the payload never enters your context.
   - **`js()` has a ~5s response cap.** One symbol per call is safe; two usually is. Loop over symbols *inside one Python process* so each `js()` call gets its own window, rather than one browser_exec call per symbol.
2. **Wait out the 429** — can be minutes to hours, not reliable.

Stooq has a JavaScript challenge that blocks plain `curl`; a real browser solves it. `malaysiastock.biz` historical URLs are not guessable — find them from the site's own AJAX calls.

**Symbol formats:** Bursa Malaysia = `<code>.KL` (e.g. `1155.KL` = Maybank), index = `^KLSE`, US = plain ticker. Verify each ticker actually returns bars before building a universe on it.

**Build the universe from a real source, not memory.** For KLCI 30, parse the `wikitable` on `en.wikipedia.org/wiki/FTSE_Bursa_Malaysia_KLCI` (table index 1; the page also carries a year-by-year index-level table, so select by header text, not position). Hand-recalled ticker lists are unreliable.

## The rig: build it so the numbers can be trusted

Before reporting any result, run these checks. A backtest that is subtly wrong is worse than no backtest.

- **Verify the indicator maths against a hand-computed reference** on a tiny known series. RSI in particular has two variants (simple vs Wilder smoothing) and they diverge materially at short periods — RSI(2) is where it shows.
- **Audit trade-level accounting against the raw CSV.** Recompute each recorded trade's return from the stored prices and require an exact match. Round recorded prices to the same precision you compute with, or the audit will report phantom mismatches at the 5th decimal.
- **Check the universe actually contains only tradable assets.** An index mixed into a stock universe gets bought like a stock and silently corrupts every result.
- **Check for same-bar round trips, zero-length holds, and non-positive prices.**

## Cost models (make them explicit, never implicit)

TradingView's Strategy Tester has no realistic cost model, which is exactly why it flatters every high-turnover strategy. Always run each variant **gross and net**, and report both.

**KLSE retail round trip = 1.350%**: brokerage 0.42% + 6% SST on brokerage, stamp duty 0.10% (sell only), clearing fee 0.03%, slippage 0.15% per side.

**Always include a cost-sensitivity sweep** — net return at 0%, 0.2%, 0.4%, 0.6%, 0.8%, 1.0% and the full retail rate. This answers the question that actually matters: *at what cost does this edge survive?* A strategy whose edge only exists below 0.35% round trip is not tradeable by a retail client, and saying so is the useful answer.

## Benchmarks: the mean lies

- **Equal-weight buy-and-hold is outlier-driven.** Across 30 names, one +2,386% stock (Press Metal, 2013-2020) lifts the mean to +109.79% while the **median is +2.00%**. Always report the median alongside the mean; the median is the honest 'typical stock' number.
- **A cap-weighted index is a different bet from equal-weight.** KLCI 30 is dominated by banks; the index returned -2.84% over 2013-2020 while the median constituent returned +2.00%. Quote both.
- **Compare risk-adjusted, not just total return.** A strategy that is invested 40% of the time should not be judged on raw return against a 100%-invested benchmark. Report Sharpe and max drawdown; the strategy's real win is usually halving drawdown, not beating return.

## Worked case: Connors RSI(2) on KLSE (what the evidence said)

A complete rig lives at `~/Desktop/klse-strategy-lab/` (fetch, engine, validate, run, analyse, README). Findings worth reusing:

- **Base (published Connors settings, 30 KLCI names, 2013-2026):** gross +13.74% TRAIN / +20.28% TEST, win rate 60%, avg +0.09-0.20% per trade, max drawdown -17%/-10% vs the index's -36%/-17%. Real but modest gross edge.
- **The 200-day trend filter is the system.** Removing it turned TRAIN into **-21.88%** with a -48% drawdown. It is the single biggest factor.
- **Volatility filter (ATR%(14) > 2.0%) genuinely helped** — gross +37.75% TRAIN / +30.82% TEST, and the sweep from 0% to 4% rises monotonically, so it is not one lucky threshold. Volume-expansion and calm-volatility filters both *hurt*.
- **At 1.35% retail round trip, every variant loses badly** (-44% to -97%). The edge only survives below ~0.35-0.40% round trip.
- **Trade count is the hidden variable.** Higher ATR% thresholds improve net results mostly by cutting trades (833 -> 43), which cuts cost drag. Report trade count next to every net result, and flag when it falls low enough to be statistically meaningless.

## Turnover is usually the real variable, not the signal

A small per-trade edge against a fixed round-trip cost is a losing game once
turnover is high — the costs scale with trade count, the edge does not. When a
strategy shows a positive gross result and a catastrophic net one, **attack
turnover before touching the signal.** Report trade count next to every net
result, and always run the cost-sensitivity sweep so the breakeven cost is
explicit.

Levers that reduce turnover, and what they actually did on KLSE data
(30 KLCI names, 2013-2026, RSI(2) mean reversion base):

| Lever | Effect |
|---|---|
| **Higher timeframe (weekly bars)** | the decisive one — 6x fewer trades, win rate 48% -> 65%, drawdown halved |
| Stricter volatility filter (raise ATR% minimum) | helps twice: bigger per-trade edge AND fewer trades |
| Cooldown after exit | modest help |
| Minimum holding period | modest help |
| Stronger entry threshold | helps |
| **ATR stop loss** | **hurts** — see below |
| Fewer concurrent positions | **hurts badly** — concentrates into worse picks |

**Do not reflexively add a stop loss.** On mean-reversion systems a stop
converts recoverable trades into realised losses: a stock that dips, bounces,
dips again, then rips gets stopped on the second dip. Adding a 2x-ATR stop
turned a +13.7% gross result into **-11.7% gross**. The conventional fix was
the most damaging change tested. Test it rather than assuming it.

**A higher timeframe changes what the indicator means.** Weekly RSI(2) is a
2-WEEK lookback, not a slower 2-day one. It is a different indicator and must
be labelled as such — never present a weekly result as 'the daily strategy,
slower'. Resample with `resample('W-FRI').agg(open=first, high=max, low=min,
close=last, volume=sum)` and rescale the trend filter too (SMA(40) weekly =
~200 trading days).

**A higher timeframe is often what makes a thin edge tradeable at all.** The
same rules that lose heavily on daily bars can be flat or positive on weekly,
purely because the trade count falls. When a client asks 'does this need a
higher timeframe?', test it — it is frequently the whole answer.

## Robustness: the tests that decide whether a result is real

- **Threshold sweep, and look for a plateau, not a peak.** A profitable band
  (e.g. ATR% 3.5-5.0% all positive in both windows) is far more reassuring than
  one lucky value. Report the whole sweep and say which value you picked and why.
- **Exclude-the-winners test.** Sort trades by return and recompute the result
  with the top 1 / 3 / 5 / 10 / 20 removed. If removing a handful flips the
  result negative, the edge is an artefact of a few outliers. Also break
  returns down per ticker: broad contribution across many names is good,
  concentration in one is fatal.
- **Small samples say little.** 61 trades over 8 years is ~8/year. State the
  count and resist dressing up a thin result.
- **Report the absolute return, not just 'it beats the index'.** +16.7% over
  13.8 years is ~1.1%/year. Beating a flat index with half its drawdown is a
  real but modest result — say so.

## Reporting results back: make it visible, not a terminal dump

A number printed to a terminal is not a deliverable for this user. He wants to
see what each filter did. Build a small local dashboard rather than describing
results in prose.

**Working pattern (stdlib only, no framework):** one `http.server`-based script
that precomputes every variant at startup, caches to JSON, and serves:

- a single HTML page with an inline `<script>` holding the data as JSON,
- `/api/state` for the same data as JSON,
- `/api/trades?variant=<name>` for per-variant trade blotters.

Keep the Python side to `json.dumps` + string replacement of the JSON into an
HTML template. No JS build step, no dependencies, works offline.

**What the page must show:** every variant as a row, with the *exact filter it
added* written out in plain language (not just a name), gross and net return in
both windows, trade count, win rate, average trade, max drawdown, Sharpe, average
hold. Mark each row `PASS` / `CAUTION` / `FAIL` by an explicit rule — e.g. PASS =
positive in both windows AND 40+ trades, so a thin-sample fluke cannot look like
a win. Pin benchmarks to the bottom; they are the yardstick, not competitors.
Add a net-return bar per window (scaled, with a centre line) because a table of
signed percentages is hard to scan. Include a written method block: survivorship,
execution model, cost breakdown, windows.

**Verify the page in a real browser, not by reading your own HTML.** Check the
row count, that filters actually filter, that the default selection applied, and
that no JS error fired. `<tr>.innerText` can come back empty in headless — use
`textContent` when probing.

**Pitfall that will bite you:** HTML collapses runs of whitespace, so a data key
containing a double space will not match an `<option>` built from that key. Use
`<option value="<index>">` and look the name up by index.

**Interpreter pitfall on this machine:** bare `python3` may resolve to a Homebrew
build with no pandas. Use `/usr/bin/python3` for anything in this lab.

## Pitfalls that cost time or credibility
- **Do not answer "which is best" with a single indicator name.** The honest finding is asset-specific — the leading indicator differs by asset class. Say so, and if a per-asset lookup exists, point at it rather than naming one magic setting.
- **Your own scripts vs community scripts are different access classes.** On a free (Basic) plan the Pine Editor is fully functional — you can write, save, apply and backtest your own scripts, and their code is always visible to you. The paywall applies to *community* scripts: open-source ones you can read and paste; protected and invite-only ones show only a screenshot and description until you pay. Do not tell the user they need a paid plan to write or paste their own script — they do not.
- **Free-plan capacity limits (verified, not capability limits):** 2 indicators per chart, 1 chart per tab, 1 indicator-on-indicator, 1-3 active price alerts that expire after ~30 days, 5,000 historical bars, no server-side alerts. Publishing: Basic can publish *private* scripts (unlimited) but not *public* ones — public, protected and invite-only publishing all require a paid plan (invite-only requires Premium).
- **The indicator cap counts scripts, not lines.** One Pine script drawing 7 lines still uses one chart slot, and a script may draw up to 64 plots. Bundling several indicators into one script is the standard free-plan workaround. Note when giving it: bundled components share one resource budget.
- **Check the Pine version before pasting.** TradingView now defaults to v6; most GitHub repos are v4/v5 and some constructs break. Say which version a script targets.
- **GitHub repos are mostly v4/v5.** Pine Script v6 is newer and some constructs break. Check the version tag before recommending a script, and say which version it targets.
- **Survivorship bias inflates every retail backtest.** Backtests run on the universe that exists *today* omit bankrupt/delisted/acquired names, so returns are overstated (published estimates: roughly 0.5–3% per year, and out-of-sample results typically 100–300 bps lower than headline). State it as an upper bound whenever you quote a backtest.
- **The original published rules are usually incomplete.** Connors' RSI(2) has no hard stop loss; dropping the 200-day filter is the single biggest killer. When you hand over rules, add the missing risk control explicitly.
- **Independent re-tests decay.** Strategies documented in a specific bull window (e.g. 1995–2007) test softer afterward. Prefer evidence that spans regimes, and note when it does not.
- **Do not restate a number you cannot attribute.** If a search result carries a win rate with no study, trade count, or date range behind it, it is marketing — leave it out or label it as such.

## Response format (MARU)
Plain text, no markdown rendering in CLI. Plain-language analogies over specs — he is not an engineer. Lead with the correction to the premise, then the evidence, then the concrete answer, then the caveats, then one short next-step offer. He wants the literal facts over reassurance: never soften a weak result into a positive framing, and do not pad a one-paragraph answer into a page.

Do not present a backtested edge as an expectation of profit, and do not offer a specific trade or allocation. Frame results as hypothetical backtests with costs included.
