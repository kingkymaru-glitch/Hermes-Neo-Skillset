# Graphify verified gotchas (graphifyy 0.9.28, this machine)

## Command/flag drift between the bundled SKILL.md and the installed binary
The `~/.claude/skills/graphify/SKILL.md` documents a top-level `graphify <path> --obsidian`
flow with `graphify export obsidian`. On the installed binary:
- `graphify --help` does NOT list `build`, `export`, `query`, `path`, `explain` at the top
  level in the truncated view — but they DO exist. `export` is a verb whose subcommands
  (`html`, `callflow-html`, `obsidian`, `wiki`, `svg`, `graphml`, `neo4j`, `falkordb`) are
  shown only when you read past the truncation (use `tail -60`).
- The top-level `--obsidian` / `--obsidian-dir` flags are NOT on the binary. Use
  `graphify export obsidian --graph PATH --dir DIR` instead. `graphify export obsidian
  --help` returns generic "Run 'graphify --help'" because the subparser is bare — the real
  args are parsed in cli.py (see `_obsidian_dir` / `--dir` handling there).
- `extract` is the headless entry point: `graphify extract <path> [--out DIR] [--code-only]
  [--mode deep] [--backend B] [--no-cluster]` and others.

## LLM-key gate (the big one)
`graphify extract <dir>` for a doc/paper/image corpus refuses without an API key:
> error: no LLM API key found (N doc/paper/image file(s) need semantic extraction).
> Set GEMINI_API_KEY or GOOGLE_API_KEY (gemini), MOONSHOT_API_KEY (kimi),
> ANTHROPIC_API_KEY (claude), OPENAI_API_KEY (openai), DEEPSEEK_API_KEY (deepseek),
> or pass --backend. A code-only corpus needs no key. Or pass --code-only ...

A notes vault = all `.md` = docs → blocked. `--code-only` skips the notes entirely (wrong).
**Bypass for structural-only (no key):** import the library directly (see scripts/).

## Edge types produced by extract_markdown
`graphify/extractors/markdown.py::extract_markdown(path)` returns nodes (file + each
heading) and edges:
- `contains` — heading→child / file→heading (the vast majority in a notes vault).
- `references` — `[[wikilink]]` and `[label]: ./other.md` reference-style links.

For a typical notes vault the graph is dominated by `contains` edges, so it's rich
internally but thin on cross-note links. Cross-note linking signal = the (low) `references`
count. This is why a notes vault "doesn't make sense" — near-zero `references`.

## cluster() return shape
`from graphify.cluster import cluster; communities = cluster(G)` → `dict[node_id -> list[int]]`
(a node may belong to multiple communities). Do NOT `Counter(communities.values())`
(`TypeError: unhashable type: 'list'`). Flatten:
```python
members = defaultdict(list)
for node, clist in communities.items():
    for c in (clist if isinstance(clist, (list, tuple)) else [clist]):
        members[c].append(node)
```

## to_obsidian / export behaviour
- `to_obsidian(G, communities, output_dir, community_labels=None, cohesion=None)`.
- Expands EVERY heading into its own note → 61 source notes can become ~689 generated
  notes. For a notes vault this is noisy; restore into a subfolder, never the root.
- Writes `.graphify_obsidian_manifest.json` and only creates `.obsidian/graph.json` if it
  doesn't exist — never clobbers the user's config. Safe + reversible on a live vault.
- Also writes `graph.canvas` (Obsidian Canvas) alongside the notes.

## Library import paths (no CLI gate)
```python
from graphify.extractors.markdown import extract_markdown
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import to_obsidian, to_json
```
Python interpreter = the graphifyy venv:
`/Users/kamarulhk/Library/Application Support/pipx/venvs/graphifyy/bin/python`
(`~/.local/bin/graphify` is a symlink into that venv). Use it for scripts; `-c` inlining
mangles newlines — write a `.py` file and run it instead.
