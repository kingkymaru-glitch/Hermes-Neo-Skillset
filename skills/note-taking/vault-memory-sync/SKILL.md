---
name: vault-memory-sync
description: Enforce two auto-behaviors — (1) after every long/multi-step task completion, write key memories + progress back to the Obsidian vault; (2) at the start of any new or memory-cleared session, read the vault first to recover context. Pair with the `obsidian` skill.
platforms: [linux, macos, windows]
---

# Vault Memory Sync

Makes the Obsidian vault the durable, auto-synced memory layer so that session memory
compaction / chat clears never lose project context. Two triggers:

## Trigger 1 — WRITE-BACK (after long-task completion)

Fire this after completing any multi-step task, a session milestone, or a decision the
user made (e.g. "migrate AnglerGO to Supabase", "approve design X", "rebrand to LunaV").

Steps:
1. Compose a durable backup of active facts: product stacks, repos, live URLs, backend
   refs, project state, decisions, conventions, user preferences.
2. If `HermesKeyMemories.md` exists in the vault, **patch it** (update the relevant section)
   rather than rewriting; otherwise `write_file` it. Keep it terse — bullet facts, not prose.
3. If a project-specific note under `Projects/` is warranted (new project, big state change),
   create/update it and link it from `VAULT MAP.md`.
4. Ensure `VAULT MAP.md` has a line pointing at `HermesKeyMemories.md` as the "read first if
   memory was cleared" entry (add once).
5. Do NOT write secrets (API keys, passwords, anon keys) into notes unless the user explicitly
   asks — reference them by project name + that they live in env/console instead.
6. **COMMIT AND PUSH.** The vault is a git repo with a private GitHub remote
   (`kingkymaru-glitch/obsidian-vault`). A note that only exists on this disk is not
   backed up — the whole point of the write-back is surviving a dead machine.
   ```
   cd /Users/kamarulhk/Documents/obsidian_maru_1
   git add -A
   git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "<what changed>"
   git push
   ```
   Commit as `kingkymaru@gmail.com` — that is the account the repo belongs to. Verify with
   `git rev-list --left-right --count origin/main...HEAD` showing `0 0` before reporting done.

The vault path is `/Users/kamarulhk/Documents/obsidian_maru_1` (see `obsidian` skill for the
authoritative resolver). Use file tools with concrete absolute paths.

## Trigger 2 — READ-FROM-VAULT (new or memory-cleared session)

**Explicit wake words (auto-fire, no extra cue needed):** when the user says **"recover"**,
**"continue from last session"**, or **"awake"** (case-insensitive, any wording containing
these), immediately read BOTH files below and resume. Do not ask the user to re-explain.

Also fire at the very start of a new chat, OR when the user says "memory was cleared",
"fresh chat", "start new session", "read the vault", or similar.

Steps (on any of the above triggers):
1. Read `/Users/kamarulhk/Documents/obsidian_maru_1/VAULT MAP.md` first.
2. Read `/Users/kamarulhk/Documents/obsidian_maru_1/HermesKeyMemories.md` (the durable backup).
3. If a multi-step build was in flight, also read `HermesProgress.md`.
4. Tell the user briefly what context you recovered, then proceed. The vault is the source
   of truth — do NOT make the user re-explain everything.

## Co-founder / team context (this user's mode)

When operating as Co-founder #3 on the AnglerGO team (Founder + Qwen CTO + Hermes), the
write-back MUST capture: task completion status, the enforced rules (e.g. "never store
binary inline in DB — Storage URL only"), and the next queued task. The `ANGlerGO_HANDOFF.md`
in the repo is the per-task source of truth; the vault note is the cross-session backup.

## Pitfalls

### The vault is version-controlled — treat it that way

- **Repo:** `kingkymaru-glitch/obsidian-vault` (PRIVATE). Branch `main` tracks `origin/main`.
- **Never `write_file` a note you have not read in full.** `write_file` OVERWRITES, and a
  220-line `Projects/CDM/CDM.md` was once destroyed down to a 25-line stub this way after
  being read only with offset/limit pagination. Use `patch` for note edits; if you must
  rewrite, `read_file` the WHOLE file first. Recovery is only possible if the file was
  committed before the clobber — check with `git show <sha>:<path>`.
- **`.gitignore` deliberately excludes** plugin binaries (`.obsidian/plugins/`),
  `workspace.json` (rewritten as panes open — pure diff noise) and `.trash/`. Everything
  else is committed, INCLUDING personal notes. Do not "helpfully" broaden the exclusions:
  a backup that silently omits things is not a backup.
- **`Sessions/` holds exported Hermes session transcripts** and the vault copy is a
  SNAPSHOT. When a new export appears at `~/progress.md`, copy it in as
  `Sessions/<session-id>.md` — it will not sync itself.
- `VAULT MAP.md` documents the remote and the exclusions, so the arrangement is
  discoverable from inside the vault without asking.

- Don't duplicate MEMORY.md into the vault verbatim every time — patch only what changed.
- Don't paste secrets. Reference them by name.
- If the vault path is unreachable, fall back to MEMORY.md and tell the user the vault sync
  couldn't run this turn.
- Writing back is cheap insurance; do it even for "small" milestones if they change project
  state (a merged PR, a decision, a rebrand).
