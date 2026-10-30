---
name: obsidian-knowledge-graph
description: "Build a navigable knowledge graph from an Obsidian vault (or any folder of notes/code) and restore it as interlinked notes. Use when the user wants to 'make sense of', clean up, organize, link, or visualize a notes vault; when they ask to connect Obsidian notes; or when they mention Graphify, a knowledge graph of their vault, orphans/duplicate-note cleanup. Covers the Graphify CLI + Python library, the LLM-key gate gotcha, structural-only extraction with no key, and safely restoring generated notes into a live vault."
---

# Obsidian / vault knowledge graph

Turn a pile of notes into a navigable, linked knowledge graph and (optionally) restore
that structure back into the vault as `[[wikilink]]`-connected notes. The reference tool
is **Graphify** (`~/.local/bin/graphify`, a pipx-installed `graphifyy` package). Graphify
is NOT an Obsidian plugin — it's a CLI + Python library that scans a folder and emits a
graph.

## Mental model (how it works)

1. **Scan** a folder → Graphify extracts nodes (files, headings) and edges (containment,
   `[[wikilinks]]`, cross-references) → `graphify-out/graph.json`.
2. **Cluster** (community detection) groups related nodes into themes.
3. **Export to Obsidian** (`export obsidian`): writes ONE `.md` per node with `[[wikilinks]]`
   to neighbors + community tags in YAML frontmatter, plus `_COMMUNITY_*.md` overview notes
   and an `.obsidian/graph.json` (community-colored graph view). A **manifest**
   (`.graphify_obsidian_manifest.json`) tracks every file Graphify owns, so it never
   clobbers the user's own notes or their `.obsidian/` config. This makes the export
   **safe to point at a live vault** and **reversible** (delete the export folder).

The "link to Obsidian" the user usually means is exactly step 3 — generated interlinked
notes that show up in Obsidian's Graph View.

## Verification-first workflow (do NOT trust `--help` blindly)

Graphify's installed CLI and the bundled SKILL.md can drift. Always confirm the installed
binary's real commands before running:

```bash
~/.local/bin/graphify --help 2>&1 | tail -60   # read the WHOLE list
~/.local/bin/graphify export   2>&1             # subcommands live under verbs
```

Verified on this machine (graphifyy 0.9.28):
- The documented top-level `--obsidian` / `build` / `export obsidian` flags in the
  ~/.claude graphify SKILL.md are **not** top-level commands on the binary. `export
  obsidian` is a **subcommand of `export`** (so `export --help` looks empty — it's not).
- The Python library is directly callable (bypasses CLI gates):
  `from graphify.extractors.markdown import extract_markdown`,
  `from graphify.build import build_from_json`,
  `from graphify.cluster import cluster`,
  `from graphify.export import to_obsidian, to_json`.

## The LLM-key gate (most important gotcha)

`graphify extract <dir>` **hard-errors if the corpus is non-code and no LLM key is set**:
> error: no LLM API key found (N doc/paper/image file(s) need semantic extraction).

A notes vault is ~100% `.md` = "docs", so the CLI refuses to run without
`GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / etc. (semantic extraction
reads prose). **Workaround for structural-only analysis (no key, free):** call the library
directly — Graphify's markdown extractor is pure-local (headings, `[[wikilinks]]`, tags)
and needs no LLM. See `scripts/build_struct.py` for the verified end-to-end pipeline
(extract → build → cluster → measure orphans/hubs/dupes → stage `to_obsidian`).

If the user WANTS semantic (prose) relationships, set an LLM key and re-run the CLI
`extract` — that costs API tokens. Always tell the user which mode you used.

**Better default for in-place interlinking (verified this session): a ZERO-LLM
TF-IDF cosine approach.** Graphify's `--backend ollama` with `llama3.2` (2B) is too
weak — it returned a near-empty graph (46/52 notes = zero nodes, only 25 edges). For a
fast, deterministic, free interlink, use the pure-numpy script `interlink_tfidf.py`
in the sibling **`graphify`** skill: it injects a reversible `## Related` block
(`[[wikilinks]]`) per note. Verified: 255 links across 52 notes, 0 broken. If you truly
want prose meaning, use `qwen2.5:14b` locally (background, uncapped).

## Restoring into a live vault — get explicit consent on shape

`to_obsidian` expands **every heading** into its own note. A 61-note vault → ~689 generated
notes (mostly heading fragments). Dumping that into the root is the opposite of "clean."
Always offer the shape choice and confirm:
1. **Full Graphify map in a subfolder** (`Vault/Graphify/`) — native export, additive,
   reversible, but noisy.
2. **Slim index I generate** — one linked note per real note, no heading explosion.
3. **Clean real notes in place** — add `[[wikilinks]]` between existing notes + delete
   true duplicates; no extra files. For the linking step use the zero-LLM TF-IDF script
   `graphify:scripts/interlink_tfidf.py` (reliable; see the `graphify` skill).

Default to (1) or (3); never silently expand headings into the vault root.

Copy the staged export into the vault (the export writes to a temp/staging dir first):
```bash
mkdir -p "$VAULT/Graphify"
cp -R "$STAGE"/. "$VAULT/Graphify"/
# reversible: rm -rf "$VAULT/Graphify"
```

## What the graph reveals (the "cleanup map")

After a structural build, report:
- **Orphans** (degree 0): notes with no links in/out — connect or archive.
- **Hubs** (high degree): the spine of the vault.
- **Duplicate files**: byte-identical files (compare `md5 -q`); safe to delete one.
- **Interlink density**: `grep -rhoE '\[\[[^]]+\]\]' --include='*.md' . | wc -l`. A near-zero
  count means the vault is a disconnected pile — that's usually why it "doesn't make sense."

Gotcha on edges for a notes vault: `extract_markdown` produces mostly `contains` (heading)
edges, NOT `references` (wikilink) edges. So a structural graph is rich in internal
heading structure but thin on cross-note links — the real cross-note linking signal is the
low `references` count.

## Pitfalls (verified)

- `cluster(G)` returns `node_id -> list[int]` (a node can be in multiple communities),
  NOT `node_id -> int`. Don't `Counter(communities.values())` — it raises
  `TypeError: unhashable type: 'list'`. Iterate and flatten.
- When building `G`, dedup raw nodes by `id` before `build_from_json` (the markdown
  extractor can emit duplicate file nodes). Iterate `G.nodes(data=True)` for downstream
  label work — raw `nodes` IDs may not all survive into `G`.
- `to_obsidian` signature: `to_obsidian(G, communities, output_dir, community_labels=None,
  cohesion=None)`. `communities` is the `node->list` dict from `cluster()`.
- Run extraction from a writable CWD; Graphify writes `graphify-out/` and a cache. Use
  `extract --out DIR` to keep builds isolated per vault.

## References
- `references/graphify-gotchas.md` — full verified command/flag drift, edge types, and the
  structural-without-key workaround notes.
- `scripts/build_struct.py` — drop-in pipeline: structural build over a vault, metrics
  (orphans/hubs/dupes/communities), stages `to_obsidian` to a temp dir. No LLM key needed.
