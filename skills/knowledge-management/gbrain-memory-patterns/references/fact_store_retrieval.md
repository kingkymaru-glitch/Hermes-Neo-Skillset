# Live fact_store retrieval (verified 2026-08-20 against ~/.hermes/memory_store.db)

## Schema that the memory tools actually touch

`facts` table columns:
- `fact_id` INTEGER PK
- `content` TEXT
- `category` TEXT (project / general / short_term / ...)
- `tags` TEXT (comma-separated, e.g. `lunav, dimension-tool, vercel`)
- `trust_score` REAL — app-managed, default 0.5
- `retrieval_count` INTEGER — app-managed, default 0 (our tools bump it)
- `helpful_count` INTEGER — app-managed, default 0 (our tools bump on --helpful)
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP
- `hrr_vector` BLOB — Hermes embeddings; NOT used by these tools (left untouched)

`entities` table: `entity_id`, `name`, ... (used for entity-linked expansion).
`fact_entities` join table: links facts <-> entities.
`facts_fts`: FTS5 virtual table over `facts.content` — **DEGRADED, see below**.

## FTS5 is DEGRADED on this store — DO NOT use MATCH

```
SELECT fact_id FROM facts_fts WHERE facts_fts MATCH 'LUNAV';   -- 0 rows
-- even though 'LUNAV' appears in facts.content (fact_id 15).
SELECT fact_id FROM facts WHERE content LIKE '%LUNAV%';         -- [15, 16]  works
```

Confirmed cause: FTS5 index is not returning matches (likely external-content
sync / index not populated). Treat MATCH as unreliable. Always fall back to LIKE.

## Correct retrieval pattern (tokenized LIKE fallback)

```python
toks = [t for t in concepts(query) if len(t) >= 3]   # lowercase, drop stopwords,
                                                     # split camelCase, drop <3-char
if toks:
    like_c = " OR ".join(["content LIKE ?" for _ in toks])
    like_t = " OR ".join(["tags LIKE ?" for _ in toks])
    params = [f"%{t}%" for t in toks] * 2
    rows = con.execute(
        f"SELECT * FROM facts WHERE ({like_c}) OR ({like_t}) "
        "ORDER BY trust_score DESC LIMIT ?", (*params, limit))
```

PITFALL: a **whole-query** LIKE (`'%full multi-word query%'`) returns nothing for
partial facts. Tokenize first. The `concepts()` helper also splits camelCase
(`R-Tessera` -> `r`, `tessera`) and strips stopwords, which is why token LIKE
finds `LUNAV`/`Dimension`/`Tool` individually.

## Tooling inventory (all at ~/.hermes/scripts/)

`gap_analyze.py` — recall + gap-scan + usage recording
- `recall "<q>" [--limit N] [--bump]` -> facts + `gaps[]` + `possibly_stale[]` + `gap_signal`
- `feedback <fact_id> [--helpful]` -> +1 `retrieval_count` (+1 `helpful_count` if --helpful)
- `delta --days N | --since <ISO>` -> facts changed in window
- `context_pack "<task>" [--max-chars N] [--tags]` -> budget-packed context string

`trust_rerank.py [--w 0.4] [--apply]` — Bayesian re-rank of `trust_score` from usage
- `eff = (helpful+1)/(retrieval+2)`  (Laplace smoothing; prior 0.5)
- `new = clamp(base*(1-w) + eff*w, 0, 1)`
- dry-run by default (just prints top movers); `--apply` persists
- only moves facts with `retrieval_count > 0`; otherwise keeps prior 0.5

`skill_capture.py --title T --calls N --steps S --evidence E [--category C]`
- auto-drafts `SKILL.md` under `~/.hermes/skills/<category>/<slug>/`
- gates on `calls >= 5` (skips trivial solves)
- MECE-safe: skips if a slug already exists anywhere (prints existing path)

## Compounding loop (verified live this session)

```
recall "<q>" --bump
  -> feedback <fact_id> --helpful   (after user confirms fact was useful)
  -> trust_rerank --apply           (periodic)
  -> skill_capture --calls 14 ...   (after any multi-step solve)
```

Live proof: fact 15 pushed to 6 retrievals / 5 helpful -> `trust_score` 0.5 -> 0.6,
persisted to store. Then reset to 0.5/0/0 to keep the store clean.

## Resilience notes

- All scripts exit 0 with JSON even on error (they are data tools, never throw to caller).
- Injection sanitizer runs on fact text BEFORE it leaves the tool (Pattern 4 in SKILL.md).
- No LLM call inside the scripts; synthesis/reasoning stays with the agent.
- Scripts write directly to `~/.hermes/memory_store.db` — back it up before --apply runs
  in anger; `trust_rerank --apply` is the only one that mutates `trust_score`.
