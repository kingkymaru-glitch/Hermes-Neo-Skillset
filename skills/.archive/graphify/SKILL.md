---
name: graphify
description: Build a local knowledge graph from a corpus (code OR Obsidian markdown) with Graphify and restore it into an Obsidian vault as interlinked notes. Covers the local-Ollama backend (zero cloud cost), the openai-package pitfall, and the Obsidian restore-noise caveat. Trigger when the user mentions "graphify", "link to Obsidian", or wants to clean up / interlink / make sense of a messy vault or docs folder.
---

# Graphify — local knowledge graph + Obsidian restore

## What it is
Graphify (`~/.local/bin/graphify`; upstream skill + version at `~/.claude/skills/graphify`, e.g. v0.9.x) turns a corpus (code OR markdown/docs) into a knowledge graph and can export it INTO an Obsidian vault as interlinked `[[wikilinks]]` notes. **No API key is required** for the structural pass; an LLM is only needed for *semantic* (meaning-based) extraction, and that LLM can be your **local Ollama** — zero cloud cost.

## When to use
- User says "link X to Obsidian", "clean up / make sense of my vault with graphify", or just "graphify".
- Task is: interlink a disconnected vault, surface orphans/duplicates/hubs, or produce a navigable concept graph.

## Core mechanism (plain)
1. **Extract**: structural (AST / heading / `[[wikilink]]` parsing — deterministic, FREE, no key) + optional *semantic* (LLM reads prose, links by meaning).
2. **Build graph**: nodes = concepts / notes / headings; edges = `contains` (heading↔note) and `references` (note↔note links).
3. **Cluster**: Louvain communities → community labels.
4. **Export**: `to_obsidian(G, communities, dir)` writes ONE `.md` per node + `_COMMUNITY_*.md` overviews, plus a `.graphify_obsidian_manifest.json` tracking every file Graphify owns.

## KEY: local LLM via Ollama (no cloud cost)
Graphify has a first-class `ollama` backend. Setup that actually works:
- Ollama must be running: `curl -s http://localhost:11434/api/tags` returns your models.
- Env: `OLLAMA_BASE_URL=http://localhost:11434/v1` and `OLLAMA_MODEL=<model:tag>` (default `qwen2.5-coder:7b`).
- **PITFALL — missing package:** the ollama backend uses the `openai` Python client internally. If `openai` isn't in Graphify's venv you get: `the 'openai' package is required for this backend but is not installed.` Fix (pipx venv path):
  `~"/Library/Application Support/pipx/venvs/graphifyy/bin/python" -m pip install openai`
- CLI: `graphify extract <path> --backend ollama`. Library: `extract_corpus_parallel(files, backend="ollama", model="...", max_concurrency=1)` (concurrency is forced to 1 for ollama).
- **Model trade-off — CORRECTED (verified this session):** `llama3.2` (2B) is **too weak** for Graphify *semantic* extraction. Even backgrounded (uncapped) it returned a near-empty graph: 46/52 notes produced ZERO nodes, only 25 edges, mostly code blocks inside notes — useless for interlinking. **Do NOT rely on llama3.2 for semantic.** For real semantic quality use `qwen2.5:14b` (9 GB, local, ~1–3 min/note) or `qwen-hermes:14b`, run in the background uncapped. For a fast, deterministic, **zero-LLM** interlink, use the pure-numpy **TF-IDF cosine** approach in `references/in-place-cleanup.md` Stage 3 / `scripts/interlink_tfidf.py` — it produced 255 clean links across 52 notes with no model dependency.
- **Semantic-cache `root` pitfall:** when calling `extract_corpus_parallel`, pass the **corpus directory** as `root` (and the output dir as `cache_root`); otherwise you get `save_semantic_cache: N source_file group(s) skipped — paths do not resolve` (Graphify #1991) and the cache is dead.
- Also: `--backend openai` reaches ANY OpenAI-compatible server via `OPENAI_BASE_URL` + `OPENAI_MODEL` (llama.cpp, vLLM, LM Studio) — same `pip install openai` applies.
- **Python Path-operator pitfall (hit this session):** never write `Path(os.environ["HOME"]) + "/Docs/x"` — `Path + str` raises `TypeError: unsupported operand type(s) for +: 'PosixPath' and 'str'`. Always use the `/` operator: `Path(os.environ["HOME"]) / "Documents" / "x"`. A broken base path silently yields an empty graph instead of erroring.
- **Zero-LLM structural extraction per note:** `from graphify.extract import extract_markdown; extract_markdown(Path("note.md"))` → `{"nodes":[...], "edges":[...]}`. Edges are `contains` (heading↔note) with `source_file` / `source_location`. Deterministic, no model, no key — good for a cleanup map or for checking whether a note's existing `[[wikilinks]]` resolve. (It does NOT emit `references` edges; those only come from semantic or your own link scan.)

## CRITICAL pitfall: Obsidian RESTORE noise
`to_obsidian` expands **every heading** into its own note. Restoring a vault graph naively = hundreds of fragment notes (61 real notes → ~689 generated). That is the OPPOSITE of "clean."
- Always stage to a scratch dir FIRST, then let the USER pick the restore mode:
  - **(a) Full map → `Vault/Graphify/` subfolder** — reversible, isolated, manifest-tracked. (User chose this.)
  - **(b) Slim hub-index** — one linked note per *real* note listing neighbors as `[[wikilinks]]`; generate yourself, NOT the native export.
  - **(c) In-place** — add `[[wikilinks]]` to the real notes + delete byte-duplicate files; no extra files. **Verified recipe in `references/in-place-cleanup.md`** — the dedupe step has a critical *repoint-before-delete* pitfall: deleting a `Name 1.md` copy silently breaks `![[Name 1]]` embeds elsewhere. Backup first, repoint, then delete.
- Reversible: delete the `Graphify/` folder, or `graphify uninstall --purge`. The manifest means Graphify never overwrites the user's own notes.

## Discovery order (don't assume — verify on disk)
- `search_files` for `graphify` binaries; read `<venv>/site-packages/graphify/__main__.py` for CLI flags (`--backend`, `--obsidian`, `--out`) and `llm.py` for `extract_corpus_parallel`, `OLLAMA_*` env handling, `_validate_ollama_base_url`.
- Upstream full reference: `~/.claude/skills/graphify/SKILL.md`. This Hermes skill captures the operational lessons; read upstream for exhaustive detail.

## Repro recipe
Exact, re-runnable command sequences for every step (prereqs, the `openai` install pitfall, structural cleanup-map, Ollama semantic test, scratch staging, vault restore) are in `references/ollama-obsidian-repro.md` — copy from there instead of retyping.

For the **in-place mode (c)** workflow — backup → md5 dedupe → repoint-before-delete → zero-LLM TF-IDF interlink — see `references/in-place-cleanup.md` and `scripts/interlink_tfidf.py`.

## Zero-LLM interlink (TF-IDF cosine) — recommended default
When you just need a "clean, interlinked vault" and semantic is too flaky/slow, the pure-numpy TF-IDF approach in `scripts/interlink_tfidf.py` is the reliable path:
- Tokenizes each real note (words ≥3 chars), builds TF-IDF vectors, cosine-similarity matrix, picks top-5 most-similar OTHER notes per note, injects a `## Related` block delimited by `<!-- graphify:related -->` markers (reversible — strip with a regex).
- This session: 52 real notes → 255 clean related links, no model, no cloud. Excludes `.obsidian/`, `Graphify/`, `copilot/`, `real_notes_backup/` so chat transcripts / generated maps / backups aren't linked.
- Run it: `python scripts/interlink_tfidf.py --vault /path/to/vault [--top 5] [--min-sim 0.02] [--dry-run]`. Back up first.

## Patterns that worked (see references/ollama-obsidian-repro.md)
- **Structural-only first (no key)** to get the cleanup map: node/edge counts, orphans (degree 0), hubs (top degree), duplicate-label detection → surfaces real dup files (md5-identical) and interlink density (`grep -rhoE '\[\[[^\]]+\]\]'`).
- **Build script pattern:** load raw `graphify-out/graph.json`, `build_from_json`, `cluster`, `to_obsidian` to a scratch dir; copy into the vault only after the user confirms.
- Validate the local LLM on ONE tiny note in the background before re-running the whole vault (small models time out on big notes under a foreground cap).

## Guardrails
- Never tell the user a Graphify feature works without testing it on disk first (this session: the skill said "no other API keys are read", but `--backend ollama`/`--backend openai` DO use local/compatible servers — verify in `llm.py`).
- Restoring into a vault is additive by default; confirm the restore mode before copying, and never delete the user's 61 real notes.
