---
name: crawl4ai-web-crawl
description: >-
  Use when the built-in web_extract/web_search tools are unavailable (no
  Firecrawl credits) and the user needs to crawl/scrape a real web page or
  site into clean LLM-ready Markdown. crawl4ai is free, open-source, runs a
  local headless Chromium, needs NO API key. Use for single-page crawl,
  batch crawl, deep-crawl, or LLM-structured extraction when web_extract fails.
license: Apache-2.0
metadata:
  author: Hermes Agent
  version: "1.0.0"
  source: https://github.com/unclecode/crawl4ai
---

# crawl4ai — free local web crawling

My built-in web_extract/web_search tools are down (no Firecrawl key). crawl4ai
(unclecode, Apache-2.0, 75k+ stars) replaces them for free — it drives a local
headless Chromium, produces clean Markdown, NO API key, NO cost.

## Environment (verified on this machine)
- Install lives in `~/crawl4ai_venv` — a **Python 3.11** venv.
- MUST NOT use system `python3` (it is 3.9.6, too old; crawl4ai needs >=3.10)
  and Python 3.14 lacks prebuilt wheels (slow source build). Use 3.11:
  `/opt/homebrew/bin/python3.11 -m venv ~/crawl4ai_venv`.
- Run scripts with: `~/crawl4ai_venv/bin/python script.py`
- CLI `crwl` and `crawl4ai-setup`/`crawl4ai-doctor` also in that venv's bin.

## Install (if venv missing)
```bash
/opt/homebrew/bin/python3.11 -m venv ~/crawl4ai_venv
~/crawl4ai_venv/bin/pip install -U pip crawl4ai
~/crawl4ai_venv/bin/crawl4ai-setup   # downloads headless chromium (~95MB)
~/crawl4ai_venv/bin/crawl4ai-doctor  # verifies
```

## Single page → Markdown (basic)
```python
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        r = await crawler.arun(url="https://example.com",
                               config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        print(r.success, r.status_code, len(r.markdown or ""))
        print((r.markdown or "")[:1000])

asyncio.run(main())
```

## Batch (multiple URLs, async concurrency)
```python
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

urls = ["https://a.com", "https://b.com", "https://c.com"]

async def main():
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        results = await crawler.arun_many(
            urls, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        for r in results:
            print(r.url, r.success, len(r.markdown or ""))

asyncio.run(main())
```

## Deep crawl (follow links, BFS up to N pages)
```python
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

async def main():
    strategy = BFSDeepCrawlStrategy(max_pages=20, max_depth=2)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        r = await crawler.arun(
            url="https://docs.example.com",
            config=CrawlerRunConfig(deep_crawl_strategy=strategy,
                                    cache_mode=CacheMode.BYPASS))
        # r.links has discovered links; r.markdown per page
```

## LLM-structured extraction (turn page into JSON)
```python
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field

class Page(BaseModel):
    title: str = Field(..., description="page title")
    key_points: list[str] = Field(..., description="3-5 key points")

async def main():
    strat = LLMExtractionStrategy(
        llm_config=LLMConfig(provider="openai/qwen",  # or "openai/gpt-4o", "ollama/...", etc.
                             api_token="YOUR_KEY_OR_SET_ENV"),
        schema=Page.model_json_schema(), extraction_type="schema",
        instruction="Extract the title and key points.")
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        r = await crawler.arun(
            url="https://example.com",
            config=CrawlerRunConfig(extraction_strategy=strat,
                                    cache_mode=CacheMode.BYPASS))
        print(r.extracted_content)  # JSON string
```
NOTE: LLM extraction needs an LLM provider key. Plain Markdown crawl (above)
needs NO key. Prefer plain crawl when only content is needed.

## Gotchas
- First run downloads Chromium (~95MB) on `crawl4ai-setup`; do it once.
- Use `CacheMode.BYPASS` during testing; `CacheMode.ENABLED` to reuse cache later.
- Headless Chromium respects `robots.txt`? No — it fetches directly. Respect
  target sites' ToS and rate-limit batch/deep crawls to be a good citizen.
- For JS-heavy SPAs, headless mode handles rendering (that's the point).
- **`CrawlerRunConfig(timeout=...)` raises `TypeError`** in the installed
  version (the kwarg was removed/renamed). Do NOT pass `timeout` — it is not a
  valid arg. Set timeouts on the tool/request side or rely on the headless
  browser default. This bit us live on 2026-07-29.
- **`web_search` may be credit-dead even though `crawl4ai` works.** When the
  built-in search/extract returns "Web tools are not configured" / "no usable
  paid credits", do NOT retry it — pivot straight to crawl4ai + search-engine
  URL crawling. See `references/osint-no-search-engine.md` for the working
  recipe (which engines return real results, which return spam/CAPTCHA, and the
  Facebook brand-page → operating-entity-page trick that surfaces hidden
  address/phone/hours).

## References
- `references/osint-no-search-engine.md` — how to do company/people OSINT when
  web_search is credit-dead: working search-engine URLs, engine-quality ranking,
  and the Facebook brand→operating-entity cross-link technique.

## Verification
Install verified 2026-07-29: crawled https://docs.crawl4ai.com → success=True,
HTTP 200, 13,935 chars Markdown, no API key.
