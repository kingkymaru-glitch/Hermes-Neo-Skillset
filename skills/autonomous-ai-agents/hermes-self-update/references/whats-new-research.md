# Answering "is there an update, and what do I get?"

Two questions, two sources. Do not merge them, and do not answer either from memory.

## 1. Version delta — local install vs published release

```bash
hermes --version          # version, channel, local <sha>, "Up to date" / "Update available"
hermes update --check     # channel, selected release, its SHA
hermes update --plan      # read-only: install kind, every profile, every service to restart
```

`--check` is authoritative for "is there one". Cross-check the published side without a
browser:

```bash
curl -s https://api.github.com/repos/NousResearch/hermes-agent/releases/latest \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tag_name'], d['published_at'])"
```

Two traps in the version number itself:

- **The tag list is not the release list.** `/tags` includes non-release tags and both
  numbering families the repo has used; take the version from `/releases/latest` or from
  `--check`, never from the newest entry in `/tags`.
- **Do not report `git describe`.** On a detached stable checkout it renders as
  `<old-tag>+N-g<sha>` (or a `+canary.<timestamp>` build), which reads like a downgrade and
  means nothing to the user. Quote `hermes --version` and the release tag.

## 2. Feature list — the release bodies, in order

Read every release body between the local version and the target, not just the newest.

| Source | Gives you |
|---|---|
| `github.com/NousResearch/hermes-agent/releases/tag/<tag>` | that tag's full body, including the "Also in the window, undocumented here on purpose" paragraph |
| `releases.sh/nousresearch` | curated rollups — fastest headline per release, good for ordering |
| `nousresearch.com` homepage announcements feed | Portal and ecosystem news: new models, official plugins, promos, hardware partnerships — none of it in release notes |
| `portal.nousresearch.com` | model catalog with per-1M pricing, free tiers, Tool Gateway tool list, subscription tiers |
| `hermes-agent.nousresearch.com/docs/llms.txt` | one-line index of every shipped feature mapped to its docs page — use for "can it do X" |

### The patch-release trap

Patch releases (`vX.Y.Z+1`, `+2`, …) ship a deliberately thin body: a PR/commit count plus a
paragraph of "Also in the window, undocumented here on purpose: …", with the full curated
notes deferred to the next minor. **That paragraph IS the feature list**, and it can cover
hundreds of PRs of new capability behind a headline that says "patch release".

Consequences:

- Never summarise a run of patch releases as "small fixes" without reading those paragraphs.
- When the user is several patches behind, the delta they care about is the union of every
  intermediate body — read them all, then group the result by what it changes for them (UI,
  plugins, delegation, models, fixes), not by release order.
- "Full curated notes ship with vX.Y.0" is not "the notes do not exist yet". The patch body
  is the only written record for that window; read it there instead of telling the user
  there is nothing to read.

## 3. Portal news is not release news

Models, official plugins, tool providers and promos ship between releases and appear only
on `nousresearch.com` / `portal.nousresearch.com`. When the question is "what's new", either
answer both halves or say which half you checked. Never quote a price, a free-tier window
or a catalog entry from memory — the catalog moves; read it.

## 4. Report shape

- State first: local version + SHA, target version, how far behind.
- Then the features that change their day, as capabilities rather than PR titles.
- Then any caveat the release notes flag for their current version.
- Then the cost of applying: which services restart (`--plan` output) and that a live session
  ends.
- Then ask before applying. Plain text, no markdown, no step log.
