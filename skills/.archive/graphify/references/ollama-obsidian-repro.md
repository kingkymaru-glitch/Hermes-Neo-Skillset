# Graphify + Ollama + Obsidian — reproduction recipe

Verified on this machine (macOS, pipx-installed `graphifyy` venv). Adjust venv path if reinstalled.

## 0. Verify prereqs
```bash
# Ollama running + model present?
curl -s http://localhost:11434/api/tags | head -c 300
ollama list | grep -E 'llama3.2|qwen2.5:14b'

# Graphify binary + venv python
~/.local/bin/graphify --help
VENV="/Users/kamarulhk/Library/Application Support/pipx/venvs/graphifyy"
"$VENV/bin/python" -c "import graphify, graphify.llm as L; print('ok', hasattr(L,'extract_corpus_parallel'))"
```

## 1. Install the ollama-backend dependency (PITFALL if missing)
```bash
"$VENV/bin/python" -m pip install openai   # fixes: "the 'openai' package is required for this backend"
```

## 2. Structural pass only (no LLM key) — get the cleanup map
```bash
VENV="/Users/kamarulhk/Library/Application Support/pipx/venvs/graphifyy"
VAULT=/Users/kamarulhk/Documents/obsidian_maru_1
"$VENV/bin/python" - <<'PY'
from pathlib import Path
from graphify.core import load_graph_json, build_from_json, cluster
raw = load_graph_json(Path(VAULT)/"graphify-out/graph.json")   # run `~/.local/bin/graphify <VAULT>` first if missing
G = build_from_json(raw)
communities = cluster(G)
print("nodes", G.number_of_nodes(), "edges", G.number_of_edges(), "communities", len(set().union(*communities.values()) if communities else []))
# orphans / hubs / dup-labels computed from G.degree and node labels
PY
```

## 3. Semantic pass with local Ollama (zero cloud cost)
Env vars (bash):
```bash
export OLLAMA_BASE_URL="http://localhost:11434/v1"
export OLLAMA_MODEL="qwen2.5:14b"     # quality; use llama3.2:latest for speed
```
Library test on ONE tiny note (background it — small models time out on big notes):
```bash
"$VENV/bin/python" - <<'PY'
import os, glob
from pathlib import Path
from graphify.llm import extract_corpus_parallel
cands = sorted([c for c in glob.glob(os.environ["HOME"]+"/Documents/obsidian_maru_1/**/*.md", recursive=True)
                if "/.obsidian/" not in c and "/Graphify/" not in c], key=lambda p: os.path.getsize(p))[:4]
res = extract_corpus_parallel([Path(c) for c in cands], backend="ollama", model=os.environ["OLLAMA_MODEL"], max_concurrency=1)
print("nodes", len(res.get("nodes",[])), "edges", len(res.get("edges",[])))
PY
```
CLI equivalent: `graphify extract <path> --backend ollama`

## 4. Stage the Obsidian export to scratch (do NOT write into vault yet)
```bash
"$VENV/bin/python" - <<'PY'
from pathlib import Path
from graphify.core import load_graph_json, build_from_json, cluster
from graphify.export import to_obsidian
VAULT=Path("/Users/kamarulhk/Documents/obsidian_maru_1")
raw=load_graph_json(VAULT/"graphify-out/graph.json"); G=build_from_json(raw); comm=cluster(G)
n=to_obsidian(G, comm, "/Users/kamarulhk/graphify-builds/maru_vault/obsidian")
print("staged notes:", n)
PY
```

## 5. Restore into vault (user-confirmed mode). Chosen mode: full map subfolder.
```bash
VAULT=/Users/kamarulhk/Documents/obsidian_maru_1
STAGE=/Users/kamarulhk/graphify-builds/maru_vault/obsidian
[ -d "$VAULT/Graphify" ] && echo "ABORT: exists" || { mkdir -p "$VAULT/Graphify"; cp -R "$STAGE"/. "$VAULT/Graphify"/; }
# verify: find "$VAULT/Graphify" -name '*.md' | wc -l  (expect ~689), manifest present
```
Reversible: `rm -rf "$VAULT/Graphify"` or `graphify uninstall --purge`.

## Notes
- `to_obsidian` expands every heading into a note → ~689 notes from 61 real notes. That's expected for the "full map" mode; prefer slim/hub-index or in-place for a tighter vault.
- Interlink density of the raw vault: `grep -rhoE '\[\[[^\]]+\]\]' "$VAULT" --include='*.md' | wc -l` (was 1 — near-zero, hence the "messy" feel).
- Byte-duplicate detection: `md5 -q` two candidate files; identical hash ⇒ byte-identical. But BEFORE deleting, grep the whole vault for `[[Name 1]]` / `![[Name 1]]` embeds and repoint them to the kept original, or you create broken links (verified this session: `CIVIL AGENT.md` held two such embeds). See `references/in-place-cleanup.md` for the full dedup+repoint sequence.
