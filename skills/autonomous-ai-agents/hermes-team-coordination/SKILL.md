---
name: hermes-team-coordination
description: "Run multi-profile Hermes teams with kanban collaboration."
version: 1.0.0
author: Neo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, multi-agent, kanban, team, profiles, collaboration]
    homepage: https://github.com/NousResearch/hermes-agent
---

# Hermes Team Coordination

Multi-profile team collaboration via kanban. Neo (default) is the lead/orchestrator. Max and Lisa are workers.

## Always-On Rules

- Neo leads: creates boards, assigns tasks, reviews results, ensures quality + security
- All profiles can use any LLM model (free or paid) — MARU decides per-agent. Default is free (meituan/longcat-2.5-preview:free via Nous Portal) but model mixing is supported and encouraged for diverse perspectives
- Tasks must complete with security and professionalism quality — Neo verifies before marking done
- When a profile's credits exhaust, switch to free model immediately — don't wait for MARU

## Setup

### 1. Create/Clone Profiles

```bash
# Clone default profile (copies config, .env, SOUL.md, skills)
hermes profile create <name> --clone --description "Role description"

# List profiles
hermes profile list
```

### 2. Set Free Model on All Profiles

```bash
HERMES_HOME=~/.hermes/profiles/<name> hermes config set model.provider nous
HERMES_HOME=~/.hermes/profiles/<name> hermes config set model.default "meituan/longcat-2.5-preview:free"
```

### 3. Add MCP Servers (per profile)

```bash
echo "Y" | HERMES_HOME=~/.hermes/profiles/<name> hermes mcp add github --command npx --args -y @modelcontextprotocol/server-github
echo "Y" | HERMES_HOME=~/.hermes/profiles/<name> hermes mcp add playwright --command npx --args -y @playwright/mcp
echo "Y" | HERMES_HOME=~/.hermes/profiles/<name> hermes mcp add codebase-memory --command uvx --args codebase-memory-mcp
```

## Kanban Workflow

### Initialize + Create Board

```bash
hermes kanban init
hermes kanban boards create <slug> --name "Display Name" --icon "🚀" --color "#8b5cf6" --switch
```

### Create Tasks (one per agent)

```bash
hermes kanban create "Task title" --assignee <profile> --body "Description" --json
```

### Start Gateway (dispatcher picks up ready tasks)

```bash
hermes gateway start
```

### Monitor

```bash
hermes kanban list
hermes kanban show <task-id>
hermes kanban log <task-id>
```

### Fix Blocked Tasks

```bash
# Reclaim stuck task
hermes kanban reclaim <task-id>

# Reassign to different profile
hermes kanban reassign <task-id> <profile>

# Unblock after fixing root cause
hermes kanban unblock <task-id>
```

## Pitfalls

- **Credit exhaustion blocks kanban workers**: If a profile's LLM credits hit $0, kanban tasks crash with "protocol violation" (worker exits without calling kanban_complete). Fix: switch profile to free model + unblock task.
- **Gateway must be running**: Without `hermes gateway start`, ready tasks stay queued forever. The dispatcher ticks every 60s.
- **Profile config keys**: Use `model.provider` and `model.default` (not `provider`/`default` at top level). The CLI warns but saves anyway.
- **MCP tools need restart**: Adding MCP servers requires a new session to pick up the tools.
- **Kanban DB is per-board**: Each board has its own SQLite DB at `~/.hermes/kanban/boards/<slug>/kanban.db`.
- **Adding a new agent to the dashboard**: the team dashboard (`~/.hermes/team-dashboard/server.py`) hardcodes the agent list in several places — the profile scan lists (gateway status + skills scan), the `AGENTS` array (name/avatar/role), and the color maps. Patch all of them, and add an avatar PNG at `~/.hermes/avatars/<profile>.png` (copy an existing one if needed), then restart the dashboard via `launchctl kickstart -k gui/$(id -u)/ai.hermes.team-dashboard`. Missing any one of these leaves the agent invisible on the board.
- **Reclaim before reassign**: Cannot reassign a running task — must `reclaim` first, then `reassign`.

## References

- `references/kanban-command-cheatsheet.md` — full command reference
