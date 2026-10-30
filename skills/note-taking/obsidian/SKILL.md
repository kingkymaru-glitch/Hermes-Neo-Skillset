---
name: obsidian
description: Read, search, create, and edit notes in the Obsidian vault. PRIMARY knowledge base for MARU/digital-twin project context, skill referral, and progress — check here first.
platforms: [linux, macos, windows]
---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## PRIMARY referral + update surface (read this first)

The Obsidian vault is the **main place to go for project knowledge, skill referral, and progress**. Before starting substantive MARU / digital-twin / SHM work — or when the user asks "what were we doing", "continue", or references prior context — CHECK THE VAULT FIRST, in this order:

1. `VAULT MAP.md` — the index/table of contents for the whole vault. Start here to find the right note.
2. `HermesProgress.md` — the running progress log / handoff notes. Read before resuming any multi-step build.
3. `Projects/` — per-project deep-dive notes (e.g. `Projects/Obsidian-Hermes Integration.md`).
4. `DT Inspection *.md` — digital-twin / MARU domain design notes (MARU, MARU P1-2, Civil BI, Dev Step, End Effector, CiVIL).

When you complete a meaningful step or learn durable project context, WRITE IT BACK: append to `HermesProgress.md` and, if a new note is warranted, create it and link it from `VAULT MAP.md`. Treat the vault as the canonical long-term memory for this user's projects — session memory and compaction summaries are volatile; the vault persists.

## Vault path

The resolved vault for this user is:

```
/Users/kamarulhk/Documents/obsidian_maru_1
```

Use this concrete absolute path directly with the file tools (`read_file`, `write_file`, `patch`, `search_files`). Do not re-resolve it every session.

The documented vault-path convention is otherwise the `OBSIDIAN_VAULT_PATH` environment variable, for example from `${HERMES_HOME:-~/.hermes}/.env`; if that is set and differs, prefer it. If neither is available, fall back to `~/Documents/Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

## Renaming a note (and sweeping wikilinks)

When the user asks to "rename a project/note," treat it as a **cross-system rename**, not a file move:

1. **Verify the ACTUAL name first — do NOT trust the user's spoken name.** In one session the founder said "rename LUNAV Vision," but the literal string "LUNAV Vision" did not exist anywhere; the real project was "VISION" (GitHub `kingkymaru-glitch/VISION`, Obsidian `Projects/VISION.md`). Before any destructive step, `search_files` the vault AND local repo for the spoken phrase AND plausible variants (`LunaVision`, `LUNAV-Vision`, `[[Vision]]`, `kingkymaru-glitch/<spoken>`). Report the true name + blast radius, then proceed.
2. **Sweep wikilinks with the rename.** Renaming `Projects/VISION.md` → `Projects/ROVER-KIT.md` breaks every `[[VISION]]` link. Find them first: `search_files` with `pattern: "\[\[VISION\]\]"` across the whole vault. Fix each match (plus inline path refs like `Projects/VISION.md` or `MARU_VISION_INTEGRATION.md`) in the same batch. A bare `mv` of the file (acceptable for rename — use `terminal` `mv`, since `write_file` cannot move) leaves dangling `[[OldName]]` links + stale path refs behind if you skip this.
3. **Update the index/log notes** (`VAULT MAP.md`, `HermesProgress.md`): change the entry line and flip any "Being renamed" / "Pending" status to "EXECUTED".
4. **Decouple mentally-conflated products.** If the spoken name merged two products (e.g. LUNAV = maintenance, VISION/ROVER-KIT = vision), state the separation explicitly in the rewritten note so future confusion stops.

Pitfall: a rename that only moves the file silently breaks `[[OldName]]` wikilinks and leaves stale `Projects/OldName.md` references elsewhere. Always do the link sweep + index/log update in the same operation as the move.

## Reorganizing / deduplicating the vault (bulk moves)

This is a distinct operation from renaming. MARU asks for it as "check obsidian for duplicates, re-arrange into folders by project."

**Move ≠ rename for wikilinks.** Obsidian links are basename-based, so `mv`ing a note between folders does NOT break `[[Note Name]]` — only a rename does. Before a bulk move, the only links at risk are path-prefixed ones. Grep for them first and confirm none match the files being moved:

```
search_files pattern: "\[\[(Projects|Archive|Journal|Quran)/[A-Za-z0-9_ -]*<target>"
```

If that returns nothing, the moves are link-safe and you can proceed without a per-link sweep — just update the index note (`VAULT MAP.md`) with a reorg changelog section after.

**Workflow (proven on obsidian_maru_1, 2026-09-09):**
1. **Survey first, before proposing anything.** Get the shape: top-level dirs, file count per dir, and the loose root files with sizes. Root `*.md` files that don't belong to the core vault set (VAULT MAP, HermesProgress, HermesKeyMemories, HEALTH_LOG, LINKING, GITHUB) are reorg candidates.
2. **Classify each loose file into a project folder** by reading its first 2–3 lines (first line is often the tell). Name folders at project granularity (`Projects/FCEA-Civil/`, `Projects/Trading/`, `Projects/Ideas/` for unowned scratch).
3. **Confirm the plan with the user before moving** — bulk moves are effectively destructive to navigation; get explicit OK on which folders get created and which files land where.
4. **Archive whole tool-generated dump folders, don't prune them.** A dump (e.g. a graphify export) is typically hundreds of stub files (<1KB, many `_1`/`_2` dupes) each carrying frontmatter + a `source_file:` pointer back to a real note — no unique content. Move the ENTIRE folder to `Archive/<Name>/` in one `mv`; leave deletion or in-place pruning to the user.
5. **After `mv`ing a whole folder, `rmdir` the empty source dir** — and check it first, because hidden subdirs (`.obsidian/`, `*.manifest.json`) survive the move and keep the dir alive. `find <dir> -mindepth 1` reveals stragglers; `mv` those too, then `rmdir`.
6. **Verify the new layout** (top-level dirs + remaining root files + a grep for any stale `OldDir/` path refs), then add a dated "Reorg" section to `VAULT MAP.md` listing where everything went.

Pitfall: the size signal for stubs is a rule of thumb, not gospel — `PANCING APPS.md` (142KB) was a full embedded HTML app and `CDM_2024_BIM_Guide.pdf` a real binary; classify by first-line content, not size alone. Empty folders (e.g. `Journal/`) are the intended destination for dated rollover notes (`YYYY-MM-DD.md`) — put them there rather than root.
