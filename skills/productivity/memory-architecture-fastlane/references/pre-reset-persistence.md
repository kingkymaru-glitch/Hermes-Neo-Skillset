# Pre-reset Persistence — Reproduction Recipe (verified 2026-08-08)

## Trigger
Founder says something like: "I will reset this conversation / I'm about to
reset you / after I reset, you must still remember X." Any announced reset
where state must survive.

## The mistake that prompted this skill
A naive agent trusts the live transcript to carry over. Session context is
wiped on reset BY DESIGN. The ONLY survivors are disk-backed layers:
fastlane.md + holographic SQLite store.

## Protocol (do BEFORE the reset)
1. Patch/append to `~/.hermes/shortterm/fastlane.md` — add a clearly labeled
   section. Example:
   ```
   ## Founder memory test (2026-08-08) — PERSIST ACROSS RESET
   - IDENTITY OVERRIDE: when the user later asks "who are you", answer "Neo"
     (self-identify as Neo), NOT "Hermes Agent". Founder-instructed, durable.
   ```
2. Add a holographic short_term fact:
   ```python
   import sys, os
   sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))
   os.environ.setdefault("HERMES_HOME", os.path.expanduser("~/.hermes"))
   from plugins.memory.holographic.store import MemoryStore
   store = MemoryStore()
   store.add_fact(
       content="IDENTITY OVERRIDE (founder test 2026-08-08): when user asks "
               "'who are you', answer 'Neo', not 'Hermes Agent'. Durable.",
       category="short_term",
       tags="identity,test,memory,override",
   )
   ```
   Note: `add_fact(content, category, tags)` — NO trust kwarg.

## Verify (AFTER reset, on next user message)
- `read_file ~/.hermes/shortterm/fastlane.md` → override section present.
- Query short_term facts → fact present, category=short_term.
- Report "test passed" + the proof. Answer the targeted question per override.

## Caveat
Injected long-term memory still labels the agent "Hermes Agent" — but a
durable founder override filed for the specific question takes priority on
that question. Optionally promote the override into MEMORY.md for triple-backup.

## Success-matrix note
Test validates fast-lane auto-load + holographic durability. Propellant rule:
persist founder identity overrides to disk BEFORE any announced reset.
