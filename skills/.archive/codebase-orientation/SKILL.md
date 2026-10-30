---
name: codebase-orientation
description: "Produce a version check + full function/feature map of a codebase into a Markdown doc — for client fork, handoff, or onboarding. Covers fact-gathering (package.json, git, registry-driven config), status classification (LIVE/SCAFFOLD/NOT BUILT), the deliverable structure, and verification."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [codebase, function-map, version-check, fork, onboarding, architecture]
    related_skills: [github:codebase-inspection]
---

# Codebase Orientation — Version Check & Function Map

Generate a single Markdown document that tells a reader (or a future client-fork
author) what a codebase IS, what version it is, what every major function does,
and what is live vs. scaffold vs. not-built. Used before duplicating/modifying a
repo, for onboarding, or for handoff.

This complements `github:codebase-inspection` (which only reports LOC/language
metrics) — orientation is about *what the code does and its maturity*, not size.

## When to Use

- "Map all the functions of X to an .md"
- "Run a version check and document the app before we fork/modify it"
- Handoff / client-delivery prep where the buyer needs the big picture
- Onboarding a new dev to a registry-driven or provider-driven app

## Methodology (order matters)

1. **Pin the version (three sources, cross-check):**
   - Read `package.json` → `version`.
   - In-code version constant if any (e.g. `APP_VERSION = 'v0.2.0-STABLE'` in App.jsx).
   - Git: `git describe --tags --always`, `git tag`, `git log --oneline -8`,
     `git branch --show-current`, `git status --short`.
   - **Report discrepancies:** package.json often lags an in-code constant and a
     git tag. State HEAD-vs-tag commit delta. Recommend one source of truth
     (bump package.json + tag the fork).

2. **Enumerate the source surface (no guessing):**
   - `search_files` target=`files` pattern=`*` in `src/` (and `server/`, `lib/`)
     to list every module.
   - Read `package.json` deps to learn the stack (React/Cesium/Supabase/etc.).
   - Find **registry/config-driven** entry points: files named `*Registry`,
     `*Service`, `*Manager`, `apiUtils`, `vite.config`. These declare features
     declaratively — the most important thing to surface for forkers.

3. **Map functions by area:**
   - Read the major modules. Grep with `search_files` output_mode=`content` using
     a combined pattern, e.g.
     `^(function|const) |export (function|default|const)|<Component|fetch|connect|useCesium`
   - Group by area (globe, layers, governance, telemetry, connection, nodes,
     persistence, panels). For each: one-line "what it does" + status + `file:line`.

4. **Classify status honestly:**
   - **LIVE** — wired and working.
   - **SCAFFOLD / DISABLED** — declared but gated (missing API key, `enabled:false`,
     placeholder row). Say what unlocks it (env var, key, Supabase table).
   - **NOT BUILT** — referenced in comments/UI but no implementation.

5. **Capture architecture:** a short ASCII tree of who calls whom (context
   providers → registries → bridge server → external vault/DB). Forkers need the
   swap paths (e.g. "replace local bridge with Supabase `nodes` table; fetch shape
   stays identical").

6. **Known gaps:** missing backend tables, orphaned assets, intentionally avoided
   techniques (and WHY — e.g. in-globe GLB crashes the renderer → use iframe).

7. **Fork/modification notes:** how to add a layer, add a governed provider, swap
   storage, the env vars used, ports (flag collisions with other local services),
   and crash caveats.

8. **Write the .md** (use `templates/function-map.md`). Then verify.

## Deliverable Structure

See `templates/function-map.md` for the skeleton. Sections:
1. Version Check (table + verdict)
2. What <PROJECT> Is (one paragraph, plain language)
3. Architecture at a Glance (ASCII)
4. Function Map by Area (tables: Function | What | Status | Location)
5. Feature Status Summary (LIVE / SCAFFOLD / NOT BUILT grid)
6. Notes for Duplication / Modification

## Pitfalls

- **Version triple-mismatch is the rule, not the exception.** Always cross-check
  package.json vs in-code constant vs git tag; report it explicitly.
- **Never invent files or symbols.** Map only what exists. If session memory or
  prior notes mention files NOT present in this repo (e.g. a *different fork's*
  `AppShell.tsx` / `AdminPanel.tsx`), flag the mismatch and map the actual code.
  (This bit us: RIINA branding notes belonged to another MARU fork; the
  `my-digital-twin` repo has no such files.)
- **Registry-driven ≠ hardcoded.** Calling out "add a layer = one object in
  layerRegistry.js; no other file changes" is the single most useful fork hint.
- **Be honest about SCAFFOLD/NOT BUILT** so a client isn't sold something unbuilt.
- **Port collisions:** if a default port clashes with another local service
  (e.g. cursor-hy3-proxy on 8787), document the safe port and the reason.
- **Crash history is durable:** if a technique is intentionally avoided, record
  the error and the workaround — future forks hit the same wall.

## Verification

- For JS/TS repos: run `npm run lint` and `npm run build`; confirm 0 errors before
  claiming done. Pure `.md` deliverables need no lint, but the *facts* cited must
  come from real file reads, not memory.
- Include a footer: "Generated <date> from repo at HEAD <sha>. Verify against
  git log / lint / build after any edits."

## References

- `templates/function-map.md` — starter skeleton to copy.
- `references/method.md` — condensed technique + the MARU example (what a real
  map looked like) for shape reference.
