# OSINT without web_search (crawl4ai + search-engine URL crawl)

Verified 2026-07-29 when the managed `web_search`/`web_extract` tools returned
"Web tools are not configured — no usable paid credits." crawl4ai still works
(local Chromium, no key). Use it to crawl search-engine result pages and target
sites directly.

## Working search-engine URL crawl
Pass the search URL straight into `AsyncWebCrawler.arun`:

- DuckDuckGo HTML (BEST for local businesses):
  `https://html.duckduckgo.com/html/?q=YOUR+QUERY`
  Returns real organic results + snippets that include contact/hours detail.
- Bing: `https://www.bing.com/search?q=YOUR+QUERY`
  Often returns SPAM/ads unrelated to the query (saw IDBI Bank, PH gambling
  for a "Bfs Tayar" query). Unreliable — treat its top results as noise.
- Google: `https://www.google.com/search?q=...`
  CAPTCHA-blocks automated crawls ("unusual traffic from your computer
  network"). Do not rely on it.
- Google Maps API URL: `https://www.google.com/maps/search/?api=1&query=...`
  Returned empty for a small local business — no verified listing resolved.

Tip: crawl SEVERAL engines/sites in one script (loop over a URL list) so one
dead/blocked engine doesn't sink the task.

## Filtering the markdown
Search-result markdown is noisy (nav links, image URLs). Keep signal lines:
```python
lines = [l for l in md.splitlines()
         if l.strip() and not l.strip().startswith("!")
         and not l.strip().startswith("[!")]
```

## Facebook brand → operating-entity cross-link (KEY TRICK)
A consumer brand page (e.g. `facebook.com/bfs.tayar`) often hides address/
phone/hours ("Tiada maklumat perhubungan untuk dipaparkan" = no contact shown).
But its own posts cross-link to its OPERATING-entity page (e.g.
`facebook.com/people/Blackfire-Store-X-Petronas-MotoExpert-Bangi/<id>/`),
which DOES expose:
- Full street address
- Phone number
- Business hours
- WhatsApp click-to-chat link (`*.wasap.my`)
Crawl BOTH the brand page AND every `/people/...` or co-tagged page it links
to. Cross-source the two to assemble the dossier.

## Local-business OSINT checklist (what to pull)
- Brand page + operating-entity page (address, phone, hours, WhatsApp)
- Instagram (`instagram.com/<handle>` shows follower/post counts in logged-out
  HTML even though posts are blocked)
- DuckDuckGo for directory snippets (99nearby, cybo, infokedai, portalkedai)
- Brands/products mentioned in post snippets (Pirelli, Sunstar, DID, etc.)
- Honest gaps to report: no website, no SSM/owner name, no price list,
  Google listing missing.

## Provenance
Used on the "Bfs Tayar" (Blackfire Store X Petronas MotoExpert Bangi) research
task, 2026-07-29. Scripts: /tmp/crawl_fb.py, /tmp/crawl_bfs.py,
/tmp/crawl_bfs2.py, /tmp/crawl_bfs3.py. Output dossier:
/Users/kamarulhk/bfs_tayar_dossier.md.
