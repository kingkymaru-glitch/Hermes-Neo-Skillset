# In-place vault cleanup + interlink (Graphify mode c) — VERIFIED recipe

Executed for real on obsidian_maru_1: 61 → 59 notes (dedupe + repoint), then a
self-contained TF-IDF interlink. NO extra files added — the "clean" outcome the
user wanted. Fully reversible via the Stage-0 backup and the `graphify:related`
markers (Stage 3).

## 0. SAFETY: backup every real note first (reversible)
```bash
VAULT=/Users/kamarulhk/Documents/obsidian_maru_1
BAK=/Users/kamarulhk/graphify-builds/real_notes_backup
mkdir -p "$BAK"
find "$VAULT" -name '*.md' -not -path '*/.obsidian/*' -not -path '*/Graphify/*' -print0 \
  | while IFS= read -r -d '' f; do
      rel=${f#"$VAULT"/}; mkdir -p "$BAK/$(dirname "$rel")"; cp "$f" "$BAK/$rel"
    done
echo "backed up: $(find "$BAK" -name '*.md' | wc -l) notes"
```

## 1. Find byte-duplicate note files (md5)
```bash
VAULT=/Users/kamarulhk/Documents/obsidian_maru_1
# group by md5; uniq -d shows only hashes appearing >1x
find "$VAULT" -name '*.md' -not -path '*/.obsidian/*' -not -path '*/Graphify/*' -exec md5 -q {} \; | sort | uniq -d
# map a suspect hash back to its files:
H=5d7722b06701bdb7fda4fb3c24f62852
find "$VAULT" -name '*.md' -not -path '*/.obsidian/*' -not -path '*/Graphify/*' -print0 \
  | while IFS= read -r -d '' f; do [ "$(md5 -q "$f")" = "$H" ] && echo "$f"; done
```
Identical hash across two filenames = exact copies. One is the duplicate to delete.

## 2. PITFALL — repoint BEFORE delete (or you break links)
A deleted `Name 1.md` copy may still be referenced by `[[Name 1]]` / `![[Name 1]]`
embeds elsewhere. Grep FIRST, repoint, THEN delete:
```bash
VAULT=/Users/kamarulhk/Documents/obsidian_maru_1
VENV="/Users/kamarulhk/Library/Application Support/pipx/venvs/graphifyy"
# find every real note that links/embeds the duplicate filename
grep -rnE "\[\[FCEA_Hermes_Developer_Instructions 1|!\[\[FCEA_Hermes_Developer_Instructions 1" \
  --include='*.md' "$VAULT" | grep -v '/Graphify/' | grep -v '/real_notes_backup/'
# repoint via python (deterministic, catches both [[ ]] and ![[ ]])
"$VENV/bin/python" - <<'PY'
import pathlib
p = pathlib.Path("CIVIL AGENT.md")
t = p.read_text()
t = t.replace("FCEA_Hermes_Developer_Instructions 1", "FCEA_Hermes_Developer_Instructions")
t = t.replace("FCEA_Project_Overview 1", "FCEA_Project_Overview")
p.write_text(t)
PY
```
Only after repointing, delete the byte-duplicate copy:
```bash
rm "$VAULT/FCEA_Hermes_Developer_Instructions 1.md"
rm "$VAULT/FCEA_Project_Overview 1.md"
```
Verify: `grep -rnE "\[\[[^]]* 1\]\]$VAULT" --include='*.md' | grep -iE "FCEA"` → expect nothing.

## 3. Interlink — ZERO-LLM TF-IDF (reliable; llama3.2 is NOT)
**CORRECTION (this session):** Graphify `--backend ollama` with `llama3.2` (2B) is
too weak for semantic extraction — even backgrounded it returned a near-empty graph
(46/52 notes = ZERO nodes, only 25 edges, mostly code blocks). Do NOT use it to
interlink. Two good options:
  (a) **Pure-numpy TF-IDF cosine** (deterministic, fast, recommended):
      `scripts/interlink_tfidf.py` — builds a similarity graph over the real notes
      and injects a `## Related` block per note. Verified: 255 links across 52 notes, 0 broken.
  (b) **Real local semantic** with `qwen2.5:14b` (9 GB) if you truly want prose meaning —
      but expect ~1–3 min/note and run in the background, uncapped.

Run the TF-IDF interlink (needs numpy — use Graphify's venv python):
```bash
VENV="/Users/kamarulhk/Library/Application Support/pipx/venvs/graphifyy"
VAULT=/Users/kamarulhk/Documents/obsidian_maru_1 \
EXCLUDE="/.obsidian/,/Graphify/,/copilot/,/real_notes_backup/" \
TOP_N=5 SIM_FLOOR=0.02 \
"$VENV/bin/python" scripts/interlink_tfidf.py
```
The script excludes chat-transcript (`copilot/`) and generated (`Graphify/`) folders
as interlinking noise, skips notes already linking a candidate, and floors weak
similarity at 0.02.

## 4. Reversible strip (if the user wants it gone)
```bash
VAULT=/Users/kamarulhk/Documents/obsidian_maru_1
# remove every injected Related block
"$VENV/bin/python" - <<'PY'
import re, glob, pathlib
VAULT = pathlib.Path("/Users/kamarulhk/Documents/obsidian_maru_1")
M, E = "<!-- graphify:related -->", "<!-- /graphify:related -->"
for c in glob.glob(str(VAULT/"**/*.md"), recursive=True):
    if any(x in c for x in ["/.obsidian/","/Graphify/","/copilot/","/real_notes_backup/"]): continue
    p = pathlib.Path(c); t = p.read_text(errors="ignore")
    t2 = re.sub(r"\n*"+re.escape(M)+r".*?"+re.escape(E)+r"\s*","\n",t,flags=re.S)
    if t2 != t: p.write_text(t2)
PY
```

## Pitfalls (verified this session)
- **`Path(...) + "/str"` raises TypeError** — always use `Path(...) / "str"`.
- **Semantic-cache `root` arg**: `extract_corpus_parallel(..., root=CORPUS_DIR)` must
  point at the corpus root, NOT the `--out` dir, or you get
  `save_semantic_cache: N source_file group(s) skipped — paths do not resolve` (Graphify #1991).
- **Repoint-before-delete** (Stage 2) is mandatory — a deleted `Name 1.md` copy silently
  breaks `![[Name 1]]` embeds elsewhere. Backup first (Stage 0) so the delete is reversible.
