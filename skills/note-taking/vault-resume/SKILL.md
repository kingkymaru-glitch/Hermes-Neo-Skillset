---
name: vault-resume
description: Resume a fresh/continuation session by reading the durable Obsidian vault FIRST and reconciling it against possibly-stale injected memory before doing any work. Use on "awake", "read the vault", "continue", or any resume-style prompt.
platforms: [linux, macos, windows]
---

# Vault-Resume Protocol

When the user opens a session with "awake", "read the vault", "continue", "what were we doing", or any resume-style prompt, your injected/session memory may be STALE or DESYNCED from ground truth. The Obsidian vault is the durable, canonical source. Read it first, reconcile conflicts, then work.

## When to use
- Fresh chat, user says "awake" / "read the vault" / "continue" / "recover memory".
- User references prior context you cannot verify in the current (empty) session memory.
- Before any substantive work on a long-running project that has a vault.

## The wake-up checklist (run UNCONDITIONALLY, before work)
1. `read_file` `VAULT MAP.md` — the index. Confirms current product names and where deep notes live.
2. `read_file` `HermesKeyMemories.md` — durable backup of active-project facts (product names, Supabase refs, migration plans, conventions). Fastest reconciliation source; it's the mirror of injected memory.
3. `read_file` `HermesProgress.md` — running progress log; read the most recent entries for last-shipped work + open blockers.
4. Spot-check the relevant `Projects/` note (and any note the user named) only if the task needs it.

Steps 1–3 are cheap (three small reads) and non-optional. Use `read_file`, not `cat`. If the user names specific files (e.g. "read VAULT MAP.md and HermesKeyMemories.md"), read exactly those.

## Reconciling stale injected memory (CRITICAL pitfall)
Injected memory can carry reversed/abandoned plans the vault never confirmed — e.g. a note says "sold product X / renamed to Y" but the vault (dated later) never recorded it, or the "new" name is actually just an internal task/file spec. Resolution order when they conflict:

1. **Vault is canonical.** A vault note dated AFTER the injected memory's reference date wins. Do not act on the injected claim if a later-dated vault entry contradicts it.
2. **Verify against ground truth before deciding.** Check the actual repo name / cwd (`terminal` `pwd` + `git log -1`), and whether the "new" product name appears as a real rename vs. an internal task spec inside the vault.
3. **Act on the vault's version**, then **correct the stale injected memory** via the `memory` tool (`replace`, keep it concise — never add a second conflicting note). This prevents the next session repeating the mistake.
4. **If genuinely ambiguous** (vault silent, repo ambiguous), ask the user ONCE via `clarify` stating the concrete conflict. Do NOT silently pick. If the user doesn't answer, apply: vault/cwd ground truth > injected memory, and record the corrected fact.

## Writing back
After a meaningful step, append to `HermesProgress.md` and link new notes from `VAULT MAP.md`. See the `obsidian` skill for the native file-tool create/append/edit workflow.

## Pitfalls
- Acting on a stale injected "rename/sale" silently changes product naming, repo assumptions, and deploy targets for the whole session — wrong. Three cheap reads prevent it.
- Don't treat an internal task/file spec (e.g. a CesiumJS refactor note) as a product rename just because its title contains the name.
- Don't overwrite the vault to match stale memory. The vault is the source of truth; injected memory is the thing to be corrected.

See `references/session-resume.md` for the full checklist and the MARU/R-Tessera reconciliation that established this rule.
