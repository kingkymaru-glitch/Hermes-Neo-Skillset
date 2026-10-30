---
name: kanban-team-ops
description: "Multi-agent kanban team workflow for Hermes profiles."
version: 1.0.0
author: Neo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, team, collaboration, hermes]
    homepage: https://github.com/NousResearch/hermes-agent
---

# Kanban Team Operations

Multi-agent kanban workflow for Hermes profiles (Neo, Max, Lisa) to collaborate on tasks. Uses the built-in `hermes kanban` system with SQLite-backed boards, gateway dispatch, and a custom dashboard.

## When to Use

- **Team task assignment**: Create boards, assign tasks to profiles, track progress
- **Multi-profile coordination**: Neo (CEO), Max (tech), Lisa (UI/testing) working in parallel
- **Progress monitoring**: Dashboard at http://127.0.0.1:8765 with Overview, Results, and RE tabs
- **Cron-driven audits**: Weekly security audits, recurring team tasks

## Quick Start

```bash
# Create a board
hermes kanban boards create <slug> --name "<Name>" --icon "🔧" --color "#22c55e" --switch

# Create a task assigned to a profile
hermes kanban create "<title>" --assignee max --body "<description>" --json

# Create a child task (blocked until parents complete)
hermes kanban create "<title>" --assignee default --parent <parent_id> --json

# Start the gateway (dispatches ready tasks to profiles)
hermes gateway start

# Check status
hermes kanban list
hermes kanban stats
```

## Team Profiles

| Profile | Role | Model |
|---------|------|-------|
| default | Neo (CEO) | custom/hive-35b |
| neo | Neo clone | custom/hive-35b |
| max | Technical expert | nous/longcat-2.5-preview:free |
| lisa | UI/Testing expert | nous/longcat-2.5-preview:free |

All profiles share: MCP servers (github, playwright, codebase-memory), team-memory skill, kanban DB.

## Dashboard

The dashboard is a Python HTTP server at `~/.hermes/team-dashboard/server.py`, managed by launchd.

```bash
# Restart dashboard
launchctl unload ~/Library/LaunchAgents/ai.hermes.team-dashboard.plist
launchctl load ~/Library/LaunchAgents/ai.hermes.team-dashboard.plist

# Check status
curl -s http://127.0.0.1:8765/api/all | python3 -m json.tool

# View logs
tail -f ~/.hermes/team-dashboard/dashboard.log
```

### Dashboard Tabs

- **Overview**: Team status, kanban stats, active tasks, team memory, event feed
- **Results**: Completed task results segmented by work type, with clickable file links
- **Reverse Engineer**: Upload binaries for Ghidra analysis, view results in real-time

## Cron Jobs

```bash
# Weekly security audit (every Monday 9am)
# Job ID: 90f2fe8bfc35
# Creates fresh board, assigns audits to max/lisa, starts gateway
```

## Pitfalls

### launchd PATH
The `hermes` binary is NOT in PATH under launchd. Always use the absolute path `/Users/kamarulhk/.local/bin/hermes` in scripts run by launchd or cron.

### Workspace Garbage Collection
Kanban workspaces at `~/.hermes/kanban/workspaces/<task_id>/` are garbage-collected after task completion. Files are moved to `~/.hermes/kanban/attachments/<task_id>/`. Always check BOTH locations when looking for deliverables.

### File Path Filtering
When filtering files by hidden directories, use `f.relative_to(base_dir).parts` NOT `f.parts`. The full path includes home directory components (e.g. `.hermes`) that start with `.` and would incorrectly filter out ALL files.

### Worker Protocol Violations
Kanban workers must call `kanban_complete` or `kanban_block` before exiting. If the agent process exits cleanly (rc=0) without calling these, it counts as a protocol violation. After 3 consecutive violations, the task is marked blocked.

**Resolving blocked tasks:** `hermes kanban complete <task-id>` fails with "unknown id or terminal state" on blocked tasks, and `hermes kanban unblock <task-id>` fails with "unknown task" — neither CLI command works for this case. The only reliable fix is direct DB update:

```bash
sqlite3 ~/.hermes/kanban.db "UPDATE tasks SET status='done', completed_at=strftime('%s','now'), result='<summary>' WHERE id='<task_id>';"
```

After updating, verify via `curl -s http://localhost:8765/api/kanban | python3 -c "import json,sys; d=json.load(sys.stdin); [print(t['id'],t['status']) for t in d['tasks']]"`.

### Parent Task Dependencies
Child tasks with `--parent` are blocked until ALL parents complete. If a parent is stuck (e.g. protocol violations), the child stays blocked. Check parent status with `hermes kanban show <child_id>` and unblock parents first.

### `hermes chat -q` is Slow
Spawning a full agent session via `hermes chat -q` takes 30-120s. For dashboard chat integration, use fire-and-forget (Popen with start_new_session=True) and return immediately. The response appears in the Thinking tab when the agent processes it.

### Gateway Dispatch
The gateway dispatches ready tasks every 60s. If a task stays `ready` for more than 2 minutes, check: (1) gateway is running (`hermes gateway status`), (2) the profile's model has credits, (3) no dispatcher lock conflict.

## File Serving

The dashboard serves workspace files via `/api/file/<task_id>/<relative_path>`. Security: paths are resolved and validated to be within the workspace directory. Content types are determined by file extension.

```python
# File serving pattern
file_path = base_dir / rel_path
file_path.resolve().relative_to(base_dir.resolve())  # Security check
if file_path.exists() and file_path.is_file():
    # Serve file
```

## Team Memory Integration

All profiles share `~/.hermes/team-memory.db` (SQLite + FTS5). The team-memory skill is auto-loaded on all profiles. Log significant events:

```python
team_memory_add('neo', 'project-name', 'action', 'Details of what happened', 'tags,for,search')
```

## Reverse Engineering Integration

The dashboard's RE tab uses the Ghidra headless bridge at `~/.hermes/kanban/attachments/t_2dd52b27/ghidra_bridge_hardened.py`. Uploads go to `~/.hermes/re-uploads/`, results to `~/.hermes/re-output/<file_id>/`.

The bridge validates file types (PE, ELF, Mach-O, .NET), enforces size limits, and runs Ghidra in a sandboxed subprocess with timeout.
