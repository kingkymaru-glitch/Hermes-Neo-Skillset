---
name: team-memory
description: "Shared team memory for Neo, Max, Lisa."
version: 1.0.0
author: Neo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [memory, team, collaboration, persistence]
    homepage: https://github.com/NousResearch/hermes-agent
---

# Team Memory

Shared persistent memory for the Hermes agent team (Neo, Max, Lisa). All profiles read/write to the same SQLite database at `~/.hermes/team-memory.db`.

## When to Use

- **Log work**: After completing a task, deploy, fix, or decision — call `team_memory_add()`
- **Recall context**: When starting a new session or picking up old work — call `team_memory_search()`
- **Team awareness**: When you need to know what other profiles did — call `team_memory_recent()`
- **Project history**: When you need the full history of a project — call `team_memory_project()`

## Quick Start

```python
from hermes_tools import terminal

# Add a memory
terminal("""python3 -c "
import sqlite3, os
from datetime import datetime
db = os.path.expanduser('~/.hermes/team-memory.db')
conn = sqlite3.connect(db)
conn.execute('INSERT INTO memories (timestamp, profile, project, action, details, tags) VALUES (?, ?, ?, ?, ?, ?)',
    (datetime.now().isoformat(), 'neo', 'lunav', 'deploy', 'Deployed V0.38', 'deploy,lunav'))
conn.commit()
conn.close()
'""")

# Search memories
terminal("""python3 -c "
import sqlite3, os
db = os.path.expanduser('~/.hermes/team-memory.db')
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT m.timestamp, m.profile, m.action, m.details FROM memories_fts f JOIN memories m ON m.id = f.rowid WHERE memories_fts MATCH ? ORDER BY m.timestamp DESC', ('deploy',)).fetchall()
for r in rows: print(f'[{r[\"profile\"]}] {r[\"action\"]}: {r[\"details\"][:80]}')
conn.close()
'""")
```

## API

### Add Memory

```python
team_memory_add(profile, project, action, details, tags="")
```

- `profile`: neo, max, or lisa
- `project`: project name (e.g. lunav, hermes, rover-kit)
- `action`: short verb (deploy, fix, audit, research, config, etc.)
- `details`: full description of what happened
- `tags`: comma-separated keywords for search

### Search Memories

```python
team_memory_search(query, limit=10)
```

Full-text search across all memories. Returns matching entries sorted by timestamp.

### Recent Memories

```python
team_memory_recent(limit=20, profile=None)
```

Get recent memories, optionally filtered by profile.

### Project History

```python
team_memory_project(project, limit=50)
```

Get all memories for a specific project, sorted by timestamp.

## Examples

```python
# Log a deployment
team_memory_add('neo', 'lunav', 'deploy', 'Deployed V0.38 to production. Fixed security headers.', 'deploy,lunav,v0.38,security')

# Search for past work
results = team_memory_search('security headers')

# What did Max do recently?
results = team_memory_recent(profile='max')

# Full LunaV history
results = team_memory_project('lunav')
```

## Notes

- Database is at `~/.hermes/team-memory.db` (WAL mode, safe for concurrent access)
- FTS5 full-text search — supports keyword matching, not semantic similarity
- All profiles share the same database — what one writes, all can read
- Timestamps are ISO 8601 — sortable and human-readable
- For semantic/vector memory, use mem0 (requires separate setup)
