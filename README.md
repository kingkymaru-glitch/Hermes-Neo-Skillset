# Hermes Neo Skillset

Curated skill library for MARU's Hermes agent profiles (neo, nini, max,
lisa, genny). Lean, non-redundant, automation-first.

**284 active skills · 31 categories · 939 archived**
(2026-11 lean restructure: 1,170 → 284 active; index weight 12.1M → 3.5M chars, −71%.)

## Layout

```
skills/<category>/<skill-name>/SKILL.md   active skills (indexed by Hermes)
skills/.archive/                          parked skills (NOT indexed)
```

## Categories

| Category | Skills |
|---|---|
| software-development | 50 |
| marketing | 49 |
| startup-founder | 35 |
| productivity | 22 |
| genjutsu | 20 |
| creative | 17 |
| matt-engineering | 12 |
| mlops | 10 |
| research | 8 |
| autonomous-ai-agents | 8 |
| devops | 6 |
| matt-productivity | 6 |
| apple | 4 |
| macos | 4 |
| automation | 4 |
| media | 4 |
| social-media | 3 |
| web | 3 |
| note-taking | 3 |
| github | 2 |
| diagnostics | 2 |
| communication | 2 |
| email | 2 |
| iot-edge | 1 |
| design | 1 |
| memory | 1 |
| frontend | 1 |
| data-science | 1 |
| deployment | 1 |
| trading | 1 |
| smart-home | 1 |

## Start here — automation & conversation

| Want to… | Skill |
|---|---|
| Drive open macOS apps (Finder, Chrome, Spotify, Mail…) | `automation/macos-app-automation` |
| Automate web pages: JS, logins, forms, extraction | `automation/browser-automation` |
| GUI automation fallback (pixels, menus, unscriptable apps) | `automation/computer-use` |
| Use the user's own logged-in browser (optional CLI) | `automation/ego-browser` |
| Build turn-by-turn by voice or typing | `communication/conversational-build` |
| Talk to Hermes (native voice mode first) | `autonomous-ai-agents/hermes-voice-conversation` |
| Founder communication + workflow rules | `communication/founder-workflow` |
| Multi-profile agent teams + kanban | `autonomous-ai-agents/hermes-team-kanban` |
| Hermes itself (config, spawn, orchestrate) | `autonomous-ai-agents/hermes-agent` |

Automation routing ladder: dedicated CLI/skill → AppleScript/Shortcuts →
browser_exec (web content) → computer_use (GUI fallback). Each skill's
intro states when to hand off to the next rung.

## Restructure policy (2026-11)

1. **No redundant skills.** One canonical skill per capability; former
   duplicates are absorbed into the winner's `references/merged/` with a
   pointer section in the winner's SKILL.md. Nothing was deleted — every
   loser's full content survives in a reference or in `.archive/`.
2. **Off-mission packs parked.** The 818-skill cybersecurity import lives
   in `skills/.archive/cybersecurity/`. Restore selectively if needed;
   do not re-import wholesale (it bloats every agent's skill index).
3. **Project skills stay.** LunaV-family, LUNASCAN, CDM, MARU, RINA and
   other repo-specific dev skills are kept — they encode hard-won lessons.
4. **Upstream harness docs** (Matt Pocock repo conventions) live in
   `matt-engineering/references/upstream-docs/`, not the skills root.

Major merges: github spokes → `software-development/github` · supabase ×7 →
`software-development/supabase-backend` · vercel ×3 → `deployment/vercel-deploy` ·
hermes-team ×5 → `autonomous-ai-agents/hermes-team-kanban` · marketing/founder
overlap ×24 → canonical `marketing/*` winners · style skills ×4 →
`communication/founder-workflow` · tdd/debug/review/grill/prototype →
canonical software-development skills.

## Install into a profile

Copy the desired category folders (or individual skill folders) into
`~/.hermes/profiles/<name>/skills/`. Markdown-only skills are safe to copy;
audit any `scripts/` before executing (see the skill-curation skill).
Do not copy `.archive/` unless you intend to restore a parked skill.

## History

See git log. Pre-restructure state: tag-less, but every moved/merged file
is recoverable via `git log --follow -- <path>` or `skills/.archive/`.
