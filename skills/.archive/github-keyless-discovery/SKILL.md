---
name: github-keyless-discovery
description: "Discover and analyze PUBLIC GitHub repos using the unauthenticated REST API — for when web_search/web_extract are unavailable, gh is unauthed, or GITHUB_TOKEN is empty. Includes a repo-vs-your-project adoption-review framework."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Discovery, OSINT, API, Adoption-Review]
    related_skills: [github-repo-management]
---

# GitHub Keyless Discovery & Adoption Review

Discover, profile, and compare public GitHub repositories **without** `web_search`, `web_extract`, `gh` auth, or a `GITHUB_TOKEN`. The unauthenticated GitHub REST API (60 req/hr per IP) covers discovery + analysis fully for a handful of lookups.

This skill complements `github-repo-management` (which covers clone/fork/settings/releases). Use this one when you need to *find and understand* a repo, especially when web tools are down.

## When to use
- `web_search` / `web_extract` return "Web tools are not configured" / Firecrawl errors.
- User says "look up / find a project called X on GitHub" and you have no search tool.
- You need to compare a discovered repo against the user's own project ("how does X differ from my app", "what can we adopt from X").

## Discovery + analysis sequence (~5 calls, within rate limit)

```bash
# 1. DISCOVER by keyword, ranked by stars
curl -s "https://api.github.com/search/repositories?q=osiris&sort=stars&order=desc&per_page=15" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'message' in d and 'items' not in d:
    print('API says:', d['message']); sys.exit(1)
for r in d.get('items', []):
    print(f\"{r['full_name']}  stars={r['stargazers_count']}  lang={r.get('language')}  forks={r.get('forks_count')}\")
    print(f\"   {(r.get('description') or '(no description)')[:130]}\")
    print(f\"   {r['html_url']}\")
"

# 2. REPO META
curl -s "https://api.github.com/repos/OWNER/REPO" | python3 -c "
import sys, json
r = json.load(sys.stdin)
for k in ['full_name','description','language','stargazers_count','forks_count','open_issues_count','created_at','pushed_at','default_branch','homepage','license','size']:
    print(f'{k}: {r.get(k)}')
"

# 3. README (raw) — no token needed for public repos
curl -s "https://api.github.com/repos/OWNER/REPO/readme" -H "Accept: application/vnd.github.raw+json" -o /tmp/repo_readme.md

# 4. LANGUAGE BREAKDOWN
curl -s --max-time 50 "https://api.github.com/repos/OWNER/REPO/languages" | python3 -c "
import sys, json
d = json.load(sys.stdin); tot = sum(d.values())
for k,v in sorted(d.items(), key=lambda x:-x[1]):
    print(f'{k}: {100*v/tot:.1f}%')
"

# 5. RECENT COMMITS
curl -s "https://api.github.com/repos/OWNER/REPO/commits?per_page=8" | python3 -c "
import sys, json
for c in json.load(sys.stdin):
    a = c['commit']['author']
    print(f\"{c['sha'][:7]}  {a['date'][:10]}  {c['commit']['message'].splitlines()[0][:70]}\")
"
```

For repo structure, list root then drill: `curl -s "https://api.github.com/repos/OWNER/REPO/contents/"` and `contents/src`, `contents/intel`, etc.

## Pitfalls (learned the hard way)
- **Never send `Authorization: token $GITHUB_TOKEN` when the var is empty.** The header becomes literally `Authorization: token ` and GitHub returns `401 Unauthorized`. For public repos, omit the header entirely — the keyless calls above work.
- **Never use `git/trees/...?recursive=1` on a repo containing `node_modules`.** It returns a massive blob that can time out at 60s and floods output with dependencies. List `contents/` and drill into subfolders instead; filter `node_modules` if you must recurse.
- **Persist JSON to a temp file (`-o /tmp/x.json`) then parse separately**, guarding `if 'message' in data`. An entry with a null `description` throws `TypeError: 'NoneType' object is not subscriptable` and aborts the loop otherwise.
- **Rate limit**: 60 req/hr/IP unauthenticated. The 5-call sequence is safe. If you need more, spread them out.

## Adoption-review framework (compare a repo to the user's project)

When asked "how does X compare to my project" or "what can we adopt from X", structure the contrast along these axes, then call out explicit non-adoptions:

1. **Purpose / domain** — what problem each solves.
2. **Map engine / scale** — 2D slippy-map vs 3D globe; globe-zoom vs structure-zoom.
3. **Framework** — Next.js/App Router vs Vite+React SPA; note durable user constraints (e.g. "never migrate to Next.js / no monorepo").
4. **Data model** — transient firehose (no long-term storage) vs persistent state (DB-backed twin/model).
5. **Module architecture** — monolith vs decoupled boxes/modules.
6. **Intelligence layer** — outward OSINT probing vs inward compliance/heuristic orchestration.
7. **User / interaction** — analyst at desk vs field engineer with hardware.

Then produce a **selective adoption table**: each external feature → your project's target → Adopt? (✅ / ◐ partial-pattern-only / ✗ not adopted) + a one-line *why*. Always include an explicit "NOT adopted" list so durable constraints and out-of-scope features stay visible. Only adopt what benefits the user's actual product — do not force every feature.

## Output style
- Label fetched facts as *verified* so the user trusts them.
- Lead with a concise ranked list for discovery; reserve deep dives for the specific repo the user picks.
- For adoption reviews, prefer a table over prose; end with a one-line net result.
