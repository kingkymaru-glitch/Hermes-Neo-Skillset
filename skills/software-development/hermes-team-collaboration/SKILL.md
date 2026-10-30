---
name: hermes-team-collaboration
description: "Set up and manage a multi-profile Hermes agent team."
version: 1.0.0
author: Neo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [team, collaboration, multi-profile, kanban, dashboard]
    homepage: https://github.com/NousResearch/hermes-agent
---

# Hermes Team Collaboration

Set up and manage multiple Hermes profiles (Neo, Max, Lisa, Genny) as a coordinated team with shared memory, kanban task boards, and a monitoring dashboard.

## When to Use

- Setting up a new Hermes profile as a clone of an existing one
- Creating shared team memory across profiles
- Coordinating work via kanban boards
- Building a monitoring dashboard for the team
- Scheduling recurring team tasks via cron jobs

## Quick Start

### 1. Create a New Profile (Clone)

```bash
hermes profile create <name> --clone --description "Role description"
```

This copies config.yaml, .env, SOUL.md, and skills from the active profile. A wrapper script is created at `~/.local/bin/<name>`.

### 2. Set Up Shared Team Memory

Create a shared SQLite+FTS5 database at `~/.hermes/team-memory.db`:

```python
import sqlite3, os
from datetime import datetime

db = os.path.expanduser('~/.hermes/team-memory.db')
conn = sqlite3.connect(db)
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('''CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    profile TEXT NOT NULL,
    project TEXT,
    action TEXT NOT NULL,
    details TEXT NOT NULL,
    tags TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)''')
conn.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    action, details, tags, content='memories', content_rowid='id'
)''')
# Add triggers for FTS sync
conn.execute('''CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, action, details, tags) VALUES (new.id, new.action, new.details, new.tags);
END''')
conn.commit()
```

All profiles read/write to the same database. Use WAL mode for concurrent access.

### 3. Create a Kanban Board

```bash
hermes kanban boards create <slug> --name "Board Name" --icon "🚀" --color "#8b5cf6" --switch
hermes kanban create "Task title" --assignee <profile> --body "Task description" --json
```

Start the gateway so tasks get picked up:

```bash
hermes gateway start
```

### 4. Set Model/Provider for All Profiles

```bash
hermes config set model.provider nous
hermes config set model.default "meituan/longcat-2.5-preview:free"
# For each profile:
HERMES_HOME=~/.hermes/profiles/<name> hermes config set model.provider nous
HERMES_HOME=~/.hermes/profiles/<name> hermes config set model.default "meituan/longcat-2.5-preview:free"
```

### 5. Add MCP Servers to All Profiles

```bash
hermes mcp add github --command npx --args -y @modelcontextprotocol/server-github
HERMES_HOME=~/.hermes/profiles/<name> hermes mcp add github --command npx --args -y @modelcontextprotocol/server-github
```

### 6. Create a Cron Job for Recurring Team Tasks

Use `cronjob_manage` with action='create'. Schedule examples:
- `"every monday 9am"` — weekly audit
- `"every day at 9am"` — daily check
- `"0 9 * * *"` — cron syntax

## Dashboard

A standalone Python dashboard can be created at `~/.hermes/team-dashboard/server.py` that reads from the kanban DB and team memory DB. Serve it via launchd for auto-start:

```bash
# Create plist at ~/Library/LaunchAgents/ai.hermes.team-dashboard.plist
launchctl load ~/Library/LaunchAgents/ai.hermes.team-dashboard.plist
```

Dashboard URL: http://127.0.0.1:8765

### Discussion Room

The dashboard includes a **Discussion Room** tab — a multi-agent discussion board where team members with different personas and LLM models debate topics. Key features:

- **4 agents**: Neo (default), Max, Lisa, Genny — each with cat avatars
- **200+ personas**: Combinatorial generation from archetypes × domains × alignments × traits × experience levels
- **Per-agent LLM switching**: Each agent can use a different model (Nous Longcat, OpenAI, Google, Anthropic, Mistral, DeepSeek) — switchable via dropdown
- **Dynamic persona switching**: Change a persona mid-conversation via the dashboard dropdown
- **Devil's advocate**: Select "Chaotic" alignment for maximum challenge
- **Discussion flow**: User creates a topic → clicks "Discuss" → agents wake up, read the topic, and post their unique perspectives as comments
- **Stop/Delete controls**: Stop kills running agent processes; Delete removes the topic and all comments
- **Round tracking**: Each Discuss click increments the round number, labeling comments so the conversation evolution is visible
- **Two discussion modes**: Parallel (all agents respond independently, faster) vs Sequential (agents respond one-by-one, each reading previous replies — deeper cross-agent reaction)
- **Auto-refresh**: While agents are discussing, the page polls every 5 seconds so new replies appear without manual refresh

#### Architecture

- **Backend**: Python `ThreadingHTTPServer` (NOT `HTTPServer` — the single-threaded version blocks the entire server while agents run, causing browser timeouts)
- **Agent wake-up**: `subprocess.Popen` spawns `hermes chat --query-file <file> --oneshot -Q` for each agent, passing the topic + all previous comments as context
- **Persona system**: Each profile has a `personas/` directory with an `active_persona` pointer file. The dashboard reads/writes this to switch personas dynamically
- **Model switching**: Each profile's `config.yaml` is updated via POST to `/api/model/set` — no terminal commands needed
- **Data persistence**: SQLite at `~/.hermes/discussion-room.db` — survives server restarts
- **Avatars**: Generated cat portraits served from `~/.hermes/avatars/<name>.png`

#### Key Pitfalls

- **Threading server is mandatory**: `HTTPServer` blocks during `subprocess.run` calls. Always use `ThreadingHTTPServer` with `daemon_threads = True` for any endpoint that spawns child processes.
- **Button debounce**: Disable buttons immediately on click, show "Posting...", re-enable only after the fetch completes. Rapid clicks create duplicate topics.
- **Date format**: SQLite returns `YYYY-MM-DD HH:MM:SS` which JS `new Date()` cannot parse. Convert to ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`) in the API layer.
- **Import shadowing**: `from urllib.parse import urlparse` inside a method shadows the module-level import, causing `UnboundLocalError`. Import at module level only.
- **Query string parsing**: `parse_qs` from `urllib.parse` must be imported at module level. `parsed.query` is a string, not a dict.
- **Sequential mode ordering**: Max → Lisa → Genny. Each agent's prompt includes all previous comments from the current round, enabling genuine cross-agent reaction.

See `hermes-team-kanban` skill for full Discussion Room architecture, API endpoints, and persona system details.

## Pitfalls

- **mem0 with local proxy fails on embeddings**: If the LLM proxy doesn't support the embeddings API, mem0 crashes with `AuthenticationError` or `ModuleNotFoundError: faiss`. Use SQLite+FTS5 instead — fully local, no external API needed.
- **`skills.auto_load` is not a recognized config key**: Setting it via `hermes config set` saves the value but Hermes may not read it. Copy skills manually: `cp -r ~/.hermes/skills/<category>/<skill> ~/.hermes/profiles/<name>/skills/`
- **Kanban workers crash without model access**: If a profile's LLM credits are exhausted, kanban workers exit with protocol violations. Ensure all profiles have a working free model configured.
- **Gateway must be running for kanban dispatch**: Tasks stay in 'ready' forever without `hermes gateway start`. The gateway hosts the dispatcher that ticks every 60s.
- **Dashboard under launchd needs absolute paths**: launchd doesn't inherit shell PATH. Use absolute paths for all binaries (e.g., `/Users/kamarulhk/.local/bin/hermes`).
- **Kanban DB schema varies**: The `events` table may not exist — it's `task_events` with columns `kind` and `payload`, not `event_type` and `data`. Always check `.schema` before querying.
- **Profile config keys differ across versions**: `hermes config set` may warn about unrecognized keys. Use `--force` to skip the notice, but verify the key is actually read by the running version.

## Notes

- All profiles share the same kanban DB at `~/.hermes/kanban.db`
- Each profile has its own `~/.hermes/profiles/<name>/` directory with isolated sessions, skills, and memory
- The gateway is shared — only one profile should run the dispatcher (others will see "another gateway already holds the dispatcher lock")
- For team memory, use the `team-memory` skill (if available) or direct SQLite access
- Kanban tasks support `--parent` for dependencies, `--assignee` for routing, and `--goal` for autonomous execution
