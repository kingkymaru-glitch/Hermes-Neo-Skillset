---
name: github-repo-harvesting
description: >-
  Clone only the parts you need from a large public GitHub repo (sparse + blobless
  partial clone) and harvest portable, offline, stdlib-only skills/scripts into
  your own ~/.hermes/skills tree. Use when the user says "take a look at this repo",
  "mine these starred repos", "is X useful to us", or points at a big "awesome-*"
  monorepo and wants only a few folders without pulling hundreds of MB of gallery
  images / node_modules / unrelated examples.
license: MIT
metadata:
  author: "Hermes Agent"
  version: "1.0.0"
  source: "derived from a session mining Shubhamsaboo/awesome-llm-apps (128k★)"
---

# GitHub Repo Harvesting (sparse partial clone + skill port)

A full `git clone` of a popular "awesome-*" or template monorepo can be 100MB–1GB
because of `docs/gallery/*` images, `node_modules`, and dozens of unrelated
example folders. You almost never want all of it. Clone selectively, then cherry-pick
the portable pieces.

## When to use
- User points at a large public repo and asks "is this useful?" / "take what's beneficial".
- You want only 1–3 subfolders (e.g. `agent_skills`, `rag_tutorials`, `examples/foo`).
- You want to lift a self-contained offline skill/script into your own skills tree.

## When NOT to use
- Repo is small (<20MB) and you'll use most of it — just `git clone --depth 1`.
- You need full history for archaeology — drop `--depth 1` (still keep sparse).

## Step 1 — Sparse + blobless partial clone (public repo, no auth needed)
```bash
cd ~
rm -rf repo && git clone --filter=blob:none --sparse --depth 1 \
  https://github.com/owner/repo.git repo
cd repo
git sparse-checkout set agent_skills rag_tutorials   # ONLY what you need
du -sh .        # expect a few MB, not hundreds
ls
```
Notes:
- `--filter=blob:none` defers file contents; `--sparse` + `sparse-checkout set`
  limits the working tree to named paths. `--depth 1` skips history.
- Append more folders later: `git sparse-checkout add <dir>`.
- `set` REPLACES the current set; use `add` to grow it.

## Step 2 — Decide what's adoptable (adaptation-review)
Before copying anything, classify each candidate:
- **Portable offline skill** (pure stdlib, read-only, no network) → port into
  `~/.hermes/skills/...` so you can actually run it on user repos.
- **Pattern reference** (tutorials, example apps in a foreign stack) → keep a
  local index / notes; re-implement the pattern in the user's stack, do NOT copy
  verbatim.
- **NOT adopted** → heavy deps (Next.js/ADK/Gemini), wrong language/runtime, or
  app templates that don't drop into the user's product. State explicitly why.

## Step 3 — Port a portable skill (copy only what the runner needs)
```bash
mkdir -p ~/.hermes/skills/github/scope-creep-detector
cp -R scope-creep-detector/SKILL.md scope-creep-detector/scripts \
      scope-creep-detector/references ~/.hermes/skills/github/scope-creep-detector/
```
Drop `README.md` (install-marketing) and `docs/`/`assets/` unless the skill
actually references them.

## Step 4 — Verify before trusting (safety gate)
```bash
# Inspect imports: only argparse/json/os/re/subprocess/sys are acceptable for offline skills
head -25 scripts/*.py
# Smoke-test against a real local repo
python3 ~/.hermes/skills/github/scope-creep-detector/scripts/scope_creep.py \
  --repo ~/my-digital-twin --base main --json
```
Refuse to port any script that imports `requests`/`urllib.request` to external
hosts or writes outside temp — those are not safe offline skills.

## Step 5 — Record the harvest
Write a short local index (e.g. `RAG_REFERENCE_FOR_MARU_RINA.md`) of which
pattern-reference folders map to which future build, and note it in memory so the
next session finds the clone + index without re-discovering them.

## Pitfalls
- Never `GET trees/...?recursive=1` on a repo with `node_modules` — returns a huge
  blob that can time out at 60s and floods output. Use `contents/` + drill instead.
- Partial clones still need the remote reachable later if you `git checkout` a path
  you didn't initially pull.
- Don't force-fit a foreign-stack template into the user's product. Pattern, not code.

## References
- `references/sparse-partial-clone.md` — worked command + observed result + porting/smoke-test detail.
