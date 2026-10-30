---
name: project-spinup
description: Spin up a new standalone project for this founder across GitHub + Obsidian + design-doc-first, gated on review before any code. Covers MARU overlays AND LunaV sub-modules. Use when starting any new repo/app/concept-doc-turned-project (VISION, LUNASCAN, etc.).
version: 1.1.0
tags: [github, obsidian, project-setup, maru, lunav, design-first, scaffolding]
license: MIT
---

# Project Spinup — Founder Workflow

## When to use
- User introduces a concept doc (RTF, notes, brain-dump) and wants it turned into a project.
- "Treat this as a single project" / "create new repo" / "set up GH + obsidian" / "lets call this project X".
- Starting a module that will later connect to MARU or another aggregation hub.
- Adding a new tab, route, or module to an EXISTING live app that already has users/data (e.g. adding a "Reservoirs" tab to LunaV Studio, a new panel in R-Tessera, or a new surface in any live SaaS).

## TRIGGER (most important)
Even if the user picks a build item (e.g. via a menu/clarify choice), **do not write code
if the project home is not yet established.** STOP, scaffold the home (name + GH repo +
Obsidian note + VAULT MAP), present the design for review, then build only after an
explicit go-ahead.

> PITFALL (this session): assistant wrote `edge_sim.py` + `EVENT_SCHEMA.md` right after the
> user selected a build item, before the project was named or repo'd. User interrupted:
> "wait, dont build anything yet." Recovery was to back out, create GH repo VISION (private,
> MIT), create Obsidian `Projects/VISION.md`, register in VAULT MAP, move the design doc into
> the repo, THEN resume design review. Lesson: **scaffold + review gate BEFORE code.**

> PITFALL (existing live app): when the user wants to add a tab/panel/route to an existing
> live app, do not jump to UI scaffolding. Run the control-surface discussion first:
> who-acts-where, data ownership, read-only vs create/edit, data flow, real vs roadmap.
> Output is a short architecture brief, not code. Build starts only after explicit go-ahead.
> **Additive-tab rule:** when inserting a new tab into an existing live app, preserve existing
> tab/nav order unless asked to rearrange. Surface the new tab as additive; do not move Home,
> 3D Digital Twin, Documents, etc. without explicit instruction.

## Verify the roadmap's hardware claims BEFORE scaffolding the doc set
A pasted roadmap (from the founder, a partner, or an AI) routinely names a GPU/vendor stack that
the actual hardware cannot run. Scaffolding a plan around an unverifiable stack wastes the whole
doc set.
- **Sanity-check every vendor + model number.** Real case (LUNAV SADO, 2026-09-29): a roadmap
  specifying "9070 Nvidia" — **no NVIDIA 9070 exists**; it is an AMD Radeon RX 9070 (RDNA4).
  Had it been accepted, the plan would have carried CUDA + TensorRT for a card that supports
  neither. A wrong vendor name silently invalidates the entire build section.
- **Confirm from the machines, not from memory.** A vault note said "idle RTX 5090" while the
  founder said "one NVIDIA + two Radeon" across three PCs — and which PC is which stayed
  unconfirmed. Resolve by probe (`nvidia-smi` / `rocminfo` / `clinfo` / `docker info | grep runtime`),
  and record the probe output as the machine's profile rather than assuming.
- **Device-agnostic is the default when the target is unconfirmed.** Write the plan so the
  algorithm layer never imports a vendor API and the backend resolves at runtime
  (cpu/cuda/opencl/hip). Then A→B porting is a build change, not a rewrite — and the doc set
  stays correct even if the hardware answer flips.
- **Surface unmeetable exit criteria as a FOUNDER DECISION, never silently edit them.** Real case:
  a Phase 1 exit of "<10 ms/frame @ 1080p" on an Apple Silicon dev machine — a property of the
  target card, not the algorithm. Keep their number, state plainly that it cannot be measured
  there, and offer (a) correctness-only on the dev box with the perf target moved to the hardware
  phase, or (b) move benchmarking to the target. Recommended option first, in the roadmap itself.

## Core rule: DESIGN-FIRST, SCAFFOLD-BEFORE-BUILD
Code is written only when BOTH hold:
1. Project home established: named, GH repo created, Obsidian note + VAULT MAP entry exist.
2. User has reviewed the design/integration map and explicitly said build (or picked a phase).

## Steps
1. **Read the concept doc; write a design/integration map (markdown).** It must:
   - State the thesis: what the project is, and how it relates to the hub (MARU).
   - Map concepts → existing code (if wiring into something that exists).
   - Define THE SEAM: the single JSON contract + ingest endpoint the hub will adopt later.
   - List phases, each independently demoable, with a "minimum believable end-to-end" subset.
   - Note open design questions for review.
   Present for review. **No code yet.**
2. **On build go-ahead, scaffold the project home:**
   a. GitHub: `gh repo create <NAME> --private --license MIT --description "..." --clone`
      (default private + MIT for this founder; confirm visibility if unsure).
   b. Obsidian: create `Projects/<NAME>.md` in the vault (ROOT_DIR = `~/Documents/obsidian_maru_1`)
      — frontmatter `tags: [maru, <name>, ...]`; body: one-liner, source, why-standalone,
      the seam, phases, design decisions, references (wikilinks).
   c. Register in `VAULT MAP.md`: add a `Projects/<NAME>.md` line under the `/Projects` list,
      and add `[[<NAME>]]` to the `<!-- graphify:related -->` Related section.
   d. Move the design doc into the repo (e.g. `<repo>/docs/`), write a `README.md`.
   e. `git add -A && git commit -m "Init <NAME>: design map + README" && git push -u origin main`.
3. **Build per agreed phase(s).** Keep each step demoable; verify before claiming done.

## Co-founded / multi-owner project (founder + partner)
When the founder launches a venture with a business/engineering partner (e.g. a new
platform built to a partner's roadmap):
- The repo lands on the FOUNDER's GitHub account (`gh repo create kingkymaru-glitch/<NAME>`).
  A partner who needs to push has NO access yet — offer to `gh repo edit <NAME>` and add
them as a collaborator, and set the commit author to `kingkymaru@gmail.com` (the
Vercel-hook-compatible identity) so future auto-deploys are not gated on authorship.
- Check the vault for an EXISTING sibling domain folder before creating the project note
  (e.g. CDM/BIM material already lived under `Projects/FCEA-Civil/`). Link those notes
  from the new project note with `[[wikilinks]]` and reference them in the Status/Context
  section — do NOT re-absorb or duplicate their content into the new note.
- Enforce the partner's build discipline when it is sound: one component per prompt,
  approved stack only, versioned builds V0.xx that are never reused.

## The "connect the dots later" architecture (founder preference)
- Build standalone modules independently; MARU is the **aggregation hub**.
- Planned MARU overlays: **situational** (exists: `SituationalEntities.jsx`), **VISION/threat**
  (this class of project), **LUNAV/maintenance** (placeholders on assets).
- Each module exposes ONE seam (JSON contract + ingest endpoint) the hub adopts later. Don't
  couple early — the hub's code stays untouched until the final wiring phase.
- **LUNAV**: maintenance-capture layer. Additive overlay (clone the `SituationalEntities`
  pattern), NOT a core rewrite. Operator-authored, slow cadence, tied to asset lifecycle.
  Differs from VISION (live, event-driven threat telemetry) only in source + cadence.

## LunaV sub-module (when parent is LunaV, not MARU)
When the new project is part of **LunaV Solutions** (SS Rover Cloud), shift conventions:
- **Design inheritance:** LunaV dark MBUX aesthetic — output mirrors that look in CLI/dashboard.
- **Obsidian links:** primary cross-link is `[[SS Rover Cloud]]`, not MARU.
- **The seam:** describe how output plugs into LunaV's existing flow (e.g., `.glb` → Cloudflare R2 via the `r2-presign` Edge Function). The LunaV repo stays untouched until the wiring phase.
- **Separate tech stack is fine:** the main LunaV app is Next.js/TS; sub-modules can be Python, Swift, etc. — they connect through a file/API contract, not shared code.

## VAULT MAP patching pitfall (double `## Related`)
Vault files can have TWO `## Related` sections: one user-authored and one inside `<!-- graphify:related -->...<!-- /graphify:related -->`. When patching the VAULT MAP to add a `[[new-project]]` wikilink, the fuzzy matcher can land on the WRONG `## Related` block and drop unrelated entries. Fix: include at least one unique line ABOVE the target `## Related` in old_string so only one section matches. After patching, grep-target the file to verify both sections are intact.

## Verification pitfall (CLI smoke tests)
When smoke-testing a stdout-emitting script under `timeout` / `head` / a pipe, Python
**block-buffers** stdout and a `timeout` kill loses the buffer → you see empty output and
wrongly think it produced nothing. Fix: run with `python3 -u`, OR redirect output to a file
(`> out.jsonl`) and read the file. Never conclude "no output" from a piped+killed run.

## References
- `references/nextjs-scaffold-pitfalls.md` — create-next-app uppercase-dir rejection,
  shadcn oklch()/hsl() token mismatch, missing `--destructive-foreground`, CLI flags,
  and how to verify a static Next shell actually contains its panels.
- `references/founder-project-conventions.md` — vault path, default repo settings, VAULT MAP
  format, the three MARU overlays, seam pattern.
- `references/cross-app-alert-pipeline.md` — control surface, data flow, and AI-layer placement
  for projects that span multiple live apps and use local-LLM alerts to glue them together.

## Related skills
- `github-repo-management` — GH repo create/clone/edit (loaded this session).
- `obsidian` (knowledge-management) + `vault-memory-sync` — vault note read/write + VAULT MAP.
- `software-development/plan` — design-map / markdown-plan authoring.
- `software-development/free-tier-saas-stack` — Next.js + Supabase + R2 + Vercel foundation.
- `software-development/r-tessera-dev` — Cesium globe command-dashboard patterns.
