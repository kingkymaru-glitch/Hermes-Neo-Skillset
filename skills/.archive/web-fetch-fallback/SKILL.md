---
name: web-fetch-fallback
description: Retrieve web page, interactive-lab, or documentation content when the managed web tools (web_search / web_extract) are unavailable (Firecrawl credits gone, "Web tools are not configured"). Fall back to terminal curl + vision_analyze on the meta image + GitHub API search to get the real content. Also governs "look at X and teach me" requests where the deliverable is a teaching, not code.
---

# web-fetch-fallback

## When to use
- `web_extract` / `web_search` return "Web tools are not configured" / "no usable paid credits" / Firecrawl error.
- The user pastes a URL and asks you to explain / teach / summarize it, but managed web tools are down.
- You need raw page HTML, SPA-rendered content, or step text from an interactive lab (KillerCoda, Katacoda, etc.).

## Steps
1. **Try web_extract once.** Some environments have it; if it works, use it. If it fails on credits/Firecrawl, fall back.
2. **Fetch the raw HTML with curl** (the terminal has network even when web tools don't):
   `curl -sS -m 30 -L "<url>"`
   SPA pages return a shell — scan it for `<script src>` bundles and `og:title` / `og:description` / `og:image` meta tags.
3. **Recover the page's purpose via the meta image.** Download the `og:image` and run `vision_analyze` on it. Lab/scenario banners often state the exact topic (e.g. a KillerCoda header revealed "Shifu Camera Demo").
4. **Find the real content source** (SPA step text is JS-loaded, not in the HTML):
   - *KillerCoda / Katacoda:* step text lives in a GitHub repo. Search `https://api.github.com/search/repositories?q=<scenario>+killercoda`, guess `<org>/killercoda-<scenario>`, then pull `intro.md` / `stepN/stepN.md` / `finish.md` via `raw.githubusercontent.com`. See `references/killercoda-scenarios.md`.
   - *General docs:* search the project's GitHub org for the topic and read the markdown via `raw.githubusercontent.com`.
5. **Teach, don't build.** When the user said "teach me about it first before any coding," the deliverable is a plain-language explanation (outcome + simple analogy before jargon). Offer implementation as a follow-up option, never start it unprompted.

## Pitfalls
- A `curl` timeout in the sandbox is NOT proof the site is down — the sandbox may be network-firewalled while the user's machine reaches it fine. This generalizes to debugging ANY live external connection (WebSocket, API, DB): a sandbox-side failure is often inconclusive. See `references/sandbox-reachability.md` for the full rule and the pattern for getting the decisive Mac-side signal.
- `web_extract` truncates large pages; `curl` gives the full shell but not the rendered DOM. Pair curl with vision on the meta image + the GitHub source for SPA content.
- Don't hand-invent page content. If you cannot fetch the real source, say so and ask the user to paste the relevant text.

## References
- `references/killercoda-scenarios.md` — exact recipe for pulling KillerCoda step content from GitHub (with the Shifu demo as a worked example).
- `references/sandbox-reachability.md` — why a sandbox-side connection failure is inconclusive, and the pattern for getting decisive proof from the user's machine.
