#!/usr/bin/env python3
"""
interlink_tfidf.py — deterministic, ZERO-LLM vault interlinking (Graphify skill).

Builds a TF-IDF cosine-similarity graph over a vault's REAL markdown notes
(excludes .obsidian/, Graphify/, copilot/ transcripts, backups by default) and
injects a clean, reversible `## Related` block ([[wikilinks]]) at the end of
each note.

WHY THIS (verified this session): llama3.2 (2B) via Graphify's `--backend ollama`
returns a near-empty semantic graph (46/52 notes produced ZERO nodes, only 25
edges, mostly code blocks). This pure-numpy TF-IDF approach is deterministic,
fast, and reliable — 255 Related links injected across 52 notes, 0 broken links.

REQUISITES: numpy. Run with Graphify's venv python:
  VAULT=/path/to/vault \
  EXCLUDE="/.obsidian/,/Graphify/,/copilot/,/real_notes_backup/" \
  TOP_N=5 SIM_FLOOR=0.02 \
  /Users/kamarulhk/Library/Application\ Support/pipx/venvs/graphifyy/bin/python interlink_tfidf.py

REVERSIBLE: every block is wrapped in `<!-- graphify:related -->` ...
`<!-- /graphify:related -->` markers; strip all with:
  grep -rl 'graphify:related' --include='*.md' $VAULT | xargs sed -i ''
  (or the regex in references/in-place-cleanup.md)
"""
import os, re, glob, math
from collections import Counter
from pathlib import Path
import numpy as np

VAULT = Path(os.environ.get("VAULT", Path.home() / "Documents" / "obsidian_maru_1"))
EXCLUDE = [s for s in os.environ.get(
    "EXCLUDE", "/.obsidian/,/Graphify/,/copilot/,/real_notes_backup/").split(",") if s]
TOP_N = int(os.environ.get("TOP_N", "5"))
SIM_FLOOR = float(os.environ.get("SIM_FLOOR", "0.02"))
MARK, END = "<!-- graphify:related -->", "<!-- /graphify:related -->"


def collect():
    out = []
    for c in glob.glob(str(VAULT / "**/*.md"), recursive=True):
        if any(x in c for x in EXCLUDE):
            continue
        out.append(Path(c))
    return sorted(out)


def main():
    notes = collect()
    linkre = re.compile(r"!?\[\[([^\]\|#]+)")
    texts = {n: n.read_text(errors="ignore") for n in notes}
    stems = {n: n.stem for n in notes}
    toks = lambda t: [w for w in re.findall(r"[a-zA-Z0-9_]+", t.lower()) if len(w) >= 3]

    docs = [toks(texts[n]) for n in notes]
    df = Counter()
    for d in docs:
        for w in set(d):
            df[w] += 1
    N = len(docs)
    idf = {w: math.log((N + 1) / (c + 1)) + 1 for w, c in df.items()}
    vocab = sorted(idf)
    idx = {w: i for i, w in enumerate(vocab)}
    V = len(vocab)

    vecs = []
    for d in docs:
        tf = Counter(d)
        v = np.zeros(V)
        L = len(d) or 1
        for w, c in tf.items():
            if w in idx:
                v[idx[w]] = (c / L) * idf[w]
        norm = np.linalg.norm(v)
        if norm > 0:
            v /= norm
        vecs.append(v)
    M = np.array(vecs)
    sims = M @ M.T

    plan = {}
    for i, n in enumerate(notes):
        row = sims[i].copy()
        row[i] = -1
        existing = {l.strip() for l in linkre.findall(texts[n])}
        picks = []
        for j in np.argsort(-row):
            if len(picks) >= TOP_N:
                break
            if stems[notes[j]] in existing:
                continue
            if row[j] <= SIM_FLOOR:
                break
            picks.append(stems[notes[j]])
        plan[str(n.relative_to(VAULT))] = picks

    changed = 0
    for relpath, picks in plan.items():
        if not picks:
            continue
        p = VAULT / relpath
        t = p.read_text(errors="ignore")
        t = re.sub(r"\n*" + re.escape(MARK) + r".*?" + re.escape(END) + r"\s*", "\n", t, flags=re.S)
        block = "\n\n" + MARK + "\n## Related\n" + "".join(f"- [[{x}]]\n" for x in picks) + END + "\n"
        t = t.rstrip("\n") + block
        p.write_text(t)
        changed += 1

    print(f"Injected Related blocks into {changed}/{len(notes)} notes; "
          f"total links={sum(len(v) for v in plan.values())}")


if __name__ == "__main__":
    main()
