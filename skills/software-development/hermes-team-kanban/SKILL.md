---
name: hermes-team-kanban
description: "Coordinate multiple Hermes profiles as a team via kanban."
version: 1.0.0
author: Neo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, team, coordination, hermes]
    homepage: https://github.com/NousResearch/hermes-agent
---

# Hermes Team Kanban

Coordinate multiple Hermes profiles (Neo, Max, Lisa, etc.) as a team using kanban boards. Each profile is an independent Hermes instance with its own config, skills, and memory. The kanban system provides shared task tracking, atomic claiming, and cross-profile visibility.

## When to Use

- Multiple Hermes profiles need to work on related tasks
- You want to assign work to specific profiles and track progress
- You need real-time visibility into what each profile is doing
- You want to coordinate parallel work (e.g., security audits across multiple projects)

## Quick Start

### 1. Create a Board

```bash
hermes kanban boards create <slug> --name "Board Name" --icon "🚀" --color "#8b5cf6" --switch
```

### 2. Create Tasks

```bash
hermes kanban create "Task title" --assignee <profile> --body "Task description" --json
```

### 3. Start the Gateway

```bash
hermes gateway start
```

The gateway dispatches ready tasks to their assigned profiles automatically.

### 4. Monitor Progress

```bash
hermes kanban list              # Board snapshot
hermes kanban stats              # Task counts by status
hermes kanban tail <task-id> --interval 5   # Real-time task feed
```

## Profile Setup

### Clone a Profile

```bash
hermes profile create <name> --clone --description "Role description"
```

### Set Model/Provider per Profile

```bash
HERMES_HOME=~/.hermes/profiles/<name> hermes config set model.provider <provider>
HERMES_HOME=~/.hermes/profiles/<name> hermes config set model.default <model>
```

### Add MCP Servers to a Profile

```bash
HERMES_HOME=~/.hermes/profiles/<name> hermes mcp add <server> --command <cmd> --args <args>
```

Pipe `echo "Y"` to auto-accept the tool enable prompt:

```bash
echo "Y" | HERMES_HOME=~/.hermes/profiles/<name> hermes mcp add github --command npx --args -y @modelcontextprotocol/server-github
```

## Task Management

### Reassign a Task

```bash
hermes kanban reclaim <task-id>    # Release if running
hermes kanban reassign <task-id> <profile>
```

### Unblock a Task

```bash
hermes kanban unblock <task-id>
```

### Create a Dependent Task (CEO Review)

```bash
hermes kanban create "Review findings" --assignee default --body "..." --parent <task1-id> --parent <task2-id>
```

## Dashboard

A standalone dashboard server provides real-time visibility:

```bash
python3 ~/.hermes/team-dashboard/server.py
```

Serves at `http://127.0.0.1:8765` with four tabs:
- **Overview** — team status, kanban stats, active tasks, memory, events
- **Results** — completed task deliverables segmented by work type, with clickable file links
- **Reverse Engineer** — upload binaries for Ghidra headless analysis
- **Skills** — radar chart + category table + profile level cards showing team capabilities
- **Discussion Room** — multi-agent discussion board with persona picker, per-agent LLM model switching, and cat avatars
- **Motion Demo** — served at `/motion-demo`, a zero-dependency HTML page showcasing scroll reveals, particle systems, micro-interactions, kinetic typography, parallax, and animated counters

### Results Tab with Deliverables

Completed tasks show clickable file links that open workspace files via `/api/file/<task_id>/<path>`. Files are served from both `~/.hermes/kanban/workspaces/<task_id>/` AND `~/.hermes/kanban/attachments/<task_id>/` (completed task workspaces get garbage-collected and moved to attachments).

**Critical file filter bug**: When filtering hidden files, use `f.relative_to(base_dir).parts` NOT `f.parts`. The full path includes `.hermes` which starts with a dot, causing ALL files to be filtered out.

### Reverse Engineer Tab

Upload a binary → Ghidra headless → `analysis.json` + `pipeline.svg` in a user-chosen folder,
plus a Recent Analyses row and a team-memory entry. Endpoints: `POST /api/re/analyze`
(multipart `file`, `place`, `name`), `GET /api/re/status`, `GET /api/re/pipeline.svg?folder=`.
Depth, including the `analysis.json` shape and the accept-list: `references/ghidra-re-tab.md`.

**The deliverable is the TARGET program's process tree — not `analysis.json`, and not a chart of
the tooling's own steps.** MARU corrected this explicitly: a diagram showing
upload → validate → stage → ghidra → extract is the wrong output. `render_process_tree_svg()`
in `server.py` draws the call tree of the binary that was reverse engineered — entry point at
the top, every call indented beneath it, imports/thunks as leaves, repeats marked "already
expanded above" — and `_process_tree_rows()` flattens the graph into indented rows. It is
written to `<output_dir>/pipeline.svg` and served at `GET /api/re/pipeline.svg?folder=`.
`render_re_pipeline_svg()` (the old stage-by-stage flowchart) has been deleted.

**Extract call edges by walking instructions, never by reading xrefs to entry points.**
Iterate each function body, keep `ins.getFlowType().isCall()`, and resolve
`ins.getReferencesFrom()` targets with `fm.getFunctionAt()` / `getFunctionContaining()`. The
older xref-based section loses call sites and mis-attributes them whenever function sizes are
unavailable. Emit the new section TAB-separated — symbol names legitimately contain colons
(C++/Rust mangling) — and parse the existing `func:name:addr:size:cc` line with
`split(":", 4)`: a 3-way split glues size and calling convention into `"96:unknown"` and
silently breaks every range/containment calculation built on it. The tree must also surface
functions reachable only through a cycle as their own roots, or they vanish from the output.

Bridge: `~/.hermes/kanban/attachments/t_2dd52b27/ghidra_bridge_hardened.py`. It sits inside a
task **attachments/** dir and `server.py` hardcodes that path in two places — copy it aside
before editing. Run it directly to check behaviour; the UI advertises no limits:

```bash
python3 ~/.hermes/kanban/attachments/t_2dd52b27/ghidra_bridge_hardened.py <binary> -d <out-dir>
```

To re-measure the ceiling across a size spread in one go — and to confirm the pipeline still
works end to end after a change — use `scripts/re_target_practice.py` (drives the live
`POST /api/re/analyze` endpoint, prints a per-target table, appends JSONL for later analysis).

Measured behaviour (re-measure if the bridge changes):

| Target | Time | Result |
|---|---|---|
| 89–367 KB app launcher (VLC / Obsidian / Chrome) | 6–11 s | 9–108 nodes — a readable tree |
| 191 KB dyld stub (Safari) | 6 s | 2 functions, **0** call edges — correct, see the pitfall below |
| 1.4 MB native app | 81 s | 4,025 functions, 8,691 nodes — SVG 191,370 px tall, 3.4 MB |
| 3.4 MB native app | 200 s | 5,937 functions, 21,256 nodes — SVG 467,800 px, 8.9 MB; `analysis.json` 53.7 MB |
| 11.5 MB app binary | 300 s timeout | **zero** output written |
| SIP system binary (`/bin/ls`) | 8 s | works — see the `copy2` pitfall below |
| fat/universal Mach-O | — | native slice extracted with `lipo` and analyzed (`arm64`/`arm64e`) |
| script / APK / zip / firmware | — | rejected — `Unsupported file type (detected: unknown)` |

**When asked to make RE handle "anything", ground the answer in a timed run, not the UI.**
A passing small-binary result proves nothing about app-sized inputs; the measured ceiling *is*
the scope proposal. Re-measure across a size spread with `scripts/re_target_practice.py`.

**Past roughly 400 KB the uncapped tree stops being usable as an image.** 21,256 nodes renders
to a 467,800 px tall SVG, which stalls a browser, and the same run writes a 53.7 MB
`analysis.json`. Reduce the tree — collapse import-only leaves, group subtrees that repeat —
never silently cap what is shown, and report the limit as a size threshold with the measured
numbers behind it rather than as "it is slow".

Pitfalls:

- **`shutil.copy2` raises `EPERM` on macOS for SIP binaries.** copy2 replays stat metadata,
  and Apple's `restricted` file flag cannot be set on a user-owned copy, so staging `/bin/ls`,
  `/usr/bin/*` or a system app dies with `[Errno 1] Operation not permitted`. Stage with
  `shutil.copyfile` — metadata is discarded anyway, since the next line chmods 0o600.
- **Slice selection happens before import, and `arm64e` must match `arm64`.** `-processor`
  cannot pick a slice: on a universal binary Ghidra aborts with `Failed to match the load spec
  to a Universal Binary Mach-O`, and without it Ghidra silently imports the first slice (usually
  `x86_64`) and reports it only as `program_info.language`. So thin the native slice with
  `lipo -thin <arch>` and import that file — a thin arm64 Mach-O reports
  `AARCH64:LE:64:AppleSilicon`. The trap is the match itself: Apple's own binaries ship `arm64e`
  (the pointer-auth variant), not `arm64`, so an equality test against the host arch finds no
  match and silently falls back to the first slice — `/bin/ls` analyzes as Intel while looking
  fixed. Match on variant (`name.startswith(host)`), never equality, and name the slice a result
  came from in the output.
- **The reported `strings` count is inflated by empty values.** Ghidra types large zero-filled
  regions as string data, and `Data.hasStringValue()` is true for those with an empty value, so
  the extractor emits one empty entry per address. A 53 KB arm64 slice reported 14,830 strings
  of which 14,797 were empty — 33 real, identical to the 33 the same binary's x86 slice
  reported. Filter `value != ""` before counting or displaying, or the metric overstates by
  orders of magnitude and a slice-selection fix looks like it exploded the data.
- **A timeout discards everything.** No partial `analysis.json` is written, so a timed-out run
  is indistinguishable from a crash and surfaces as an empty results panel.
- **A small function count is usually correct, not broken — including a tree with zero edges.**
  Launcher stubs legitimately yield single-digit functions. A ~120 KB `Discord` main executable
  gives ~9 functions and only bootstrap symbols, with the real code in the framework/`.asar`;
  Safari's launcher gives 2 functions and **no** call edges at all, because it `dlopen`s
  `Safari.framework` and hands off through an indirect call, so there is nothing to resolve as a
  direct edge. Its strings name that framework, which is the evidence the result is right. Read
  the strings and symbols before reporting an analysis as faulty.

### Skills Tab

The Skills tab visualizes team capabilities across profiles:

- **Radar Chart** — SVG radar showing each profile's skill distribution across categories (Engineering, Marketing, Productivity, Memory, Communication, Security, Design, Data). Each profile is a colored polygon.
- **Category Table** — Table with progress bars showing skill counts per category per profile.
- **Profile Level Cards** — Cards showing each profile's total skills, level, and top categories.

**Level measurement (1-5 scale based on total skill count):**
- Level 1 (Awareness): 0-49 skills
- Level 2 (Familiar): 50-99 skills
- Level 3 (Practiced): 100-149 skills
- Level 4 (Proficient): 150-199 skills
- Level 5 (Expert): 200+ skills

**Skill scanning approach:** Use `rglob("SKILL.md")` to find all skill files, parse YAML frontmatter for name/description, classify by path keywords into categories. Limit to 50 skills per profile for performance.

**Skill sources:** Skills can be cloned from GitHub repos and copied to `~/.hermes/skills/<category>/` and each profile's `~/.hermes/profiles/<name>/skills/` directory. Proven sources:
- `mattpocock/skills` — engineering + productivity skills
- `coreyhaines31/marketingskills` — CRO, SEO, copywriting, ads, analytics
- `mukul975/Anthropic-Cybersecurity-Skills` — 817 security skills (MITRE, NIST, OWASP)
- `shawnpang/startup-founder-skills` — fundraising, sales, B2B, negotiation
- `kwakseongjae/oh-my-design` — design system generation (tokens.css, theme.config.ts)
- `AThevon/genjutsu` — creative coding, motion, UI/UX pro max

**Free art pipeline:** The `free-art-pipeline` skill (in `~/.hermes/skills/creative/`) provides zero-cost art generation using ComfyUI (local), fal (free tier), p5js (code-based), ASCII art, and SVG. No paid APIs required.

**Paid skill removal:** When deploying art/image generation skills, verify the API cost. Skills like banana-claude (Gemini), higgsfield (paid account), and agnes (paid API) were removed in favor of the free pipeline. Always check if a skill requires a paid API key before deploying.

### Dashboard Theme

Dashboard uses a black theme: pure black (#000000) background, #1a1a1a cards, #333333 borders, white/light gray text. User explicitly requested black over blueish themes.

### Animated Dashboard

The dashboard incorporates motion design principles for a polished, alive feel:

**Background Animations:**
- **Particle System** — 50 ambient particles on a fixed canvas, GPU-accelerated, wraps around screen edges
- **Animated Cat** — Two SVG cats walk across the bottom with CSS keyframe animation (leg walk, tail wag). One large/fast, one small/slow for parallax depth. Pure SVG + CSS, no JS libraries.

**UI Animations:**
- **Tab Transitions** — Fade + slide via CSS keyframes on `.tab-content.active`
- **Scroll Reveal** — Cards fade/slide in via Intersection Observer (threshold: 0.1, rootMargin: -50px)
- **Hover Effects** — Cards lift (translateY(-2px)), task items slide right (translateX(4px)), buttons squash on click (scale(0.97))
- **Micro-interactions** — Squash & stretch on press, magnetic hover on buttons

**Performance Patterns:**
- All animations use `transform` and `opacity` only (GPU-composited properties)
- `requestAnimationFrame` for canvas animations (no setTimeout loops)
- Passive event listeners for scroll/mouse (`{ passive: true }`)
- Intersection Observer for scroll reveals (no scroll event jank)
- Visibility API — canvas animations pause when tab hidden

**Accessibility:**
- `prefers-reduced-motion` media query disables ALL animations
- Canvas animations check `prefers-reduced-motion` before starting
- ARIA labels on all interactive elements
- Keyboard navigable

**Security:**
- Zero dependencies — pure CSS + vanilla JS
- No external requests, no API keys, no tracking
- All animation code is self-contained in the HTML

**Motion Design Principles Applied:**
- Disney's 12 principles adapted for web (squash & stretch, anticipation, staging, follow through)
- Spring physics via cubic-bezier easing (0.22, 1, 0.36, 1)
- Staggered reveals for visual hierarchy
- 60fps target — only transform/opacity animations

### Innovator Mode (6-Stage Pipeline)

Creates a pre-wired innovation pipeline on a new board. Each stage is a task, linked with parent dependencies so Stage N+1 doesn't start until Stage N completes.

```bash
python3 ~/.hermes/kanban/innovator.py --goal "AI-powered plant disease detector" --board my-project
```

Stages:
1. Discovery (genny) — research scan
2. Gap Analysis (genny) — identify opportunities
3. Innovation (lisa) — synthesize new concepts
4. Market Research (genny) — commercial data
5. Strategy (max) — business plan
6. Implementation (max) — operations outline

**Dashboard integration**: The Overview tab has a "Launch Innovator" button (Neo cat avatar + purple button) that POSTs to `/api/innovator/launch` with `{goal, board}`. The server runs the innovator script and returns the created task IDs.

**Desktop plugin**: `~/.hermes/desktop-plugins/kanban-board/plugin.js` adds a cat icon to the Hermes desktop status bar. Click opens the dashboard. Also adds a ⌘K palette command. Users must reload desktop plugins (⌘K → "Reload desktop plugins") to activate.

**Verification step (REQUIRED)**: After creating the pipeline, verify ALL of the following:
1. Tasks are on the correct board: `hermes kanban list` (check header shows the right board slug)
2. Dependencies are linked: `hermes kanban show <first-task-id>` (should show children)
3. Gateway dispatches them: `hermes gateway start` then wait 60s and check `hermes kanban list`
4. Trace tab shows the flow: open dashboard → click "🔀 Trace" tab → verify nodes + edges render
5. Discussion Room works: create a topic → click "Discuss" → verify agents respond

**CRITICAL BUG: `--board` flag position**: `hermes kanban --board <slug> create ...` — the flag goes RIGHT AFTER `kanban` and BEFORE `create`. Putting it at the end (`create ... --board`) or before `hermes` is SILENTLY IGNORED and tasks land on the wrong board. The innovator.py script handles this via args slicing in `run_hermes()`.

**CRITICAL BUG: boards create --switch doesn't switch**: `hermes kanban boards create <slug> --switch` creates the board but does NOT change current board. Always explicitly run `hermes kanban boards switch <slug>` before creating tasks. The innovator.py script now does this.

**Deliver results, not just tools**: When MARU asks to "use the board" or "try Innovator mode", he expects the agent to RUN the pipeline, do the research, and deliver finished proposals — not just build the script and hand it over. The workflow is: create pipeline → start gateway → wait for completion → synthesize results → present findings. If the gateway dispatcher isn't picking up tasks, debug it (check `hermes gateway status`, check task status with `hermes kanban list`, check for `last_failure_error` on tasks).

### Trace Tab (LangSmith-style)

Dashboard tab that renders task execution as a live flow graph:
- Nodes = tasks (colored by status: green=done, purple=running, yellow=ready, red=blocked)
- Arrows = parent->child dependencies
- Click node → see runs, events, results in side panel
- Event stream shows all task_events in real-time
- Data source: `/api/trace` (aggregates across ALL board DBs)

The dashboard now queries ALL kanban DBs (global + every board), not just the current board. This fixes the stale-data bug where tasks created on board A wouldn't appear when board B was active. The `query_all_kanban_dicts()` helper merges results by deduplicating on `id` or `task_id`.

**PERF BUG**: Never include trace data in `/api/all` (polled every 5s). It runs JOINs across 11 board DBs and freezes the browser with infinite refresh. Keep trace in a separate `/api/trace` endpoint that only loads when the user clicks the Trace tab.

**Browser cache**: After dashboard code changes, MARU's browser may serve cached HTML. Tell him to Cmd+Shift+R or open a private window. Verify new tabs exist by curling the page.

### Auto-start on Boot

Create `~/Library/LaunchAgents/ai.hermes.team-dashboard.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.hermes.team-dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/kamarulhk/.hermes/team-dashboard/server.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/kamarulhk/.hermes/team-dashboard/dashboard.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/kamarulhk/.hermes/team-dashboard/dashboard.log</string>
</dict>
</plist>
```

Load/unload:

```bash
launchctl load ~/Library/LaunchAgents/ai.hermes.team-dashboard.plist
launchctl unload ~/Library/LaunchAgents/ai.hermes.team-dashboard.plist
```

## Pitfalls

- **Browser cache**: After restarting the dashboard, the browser may serve a cached HTML page that lacks new tabs (e.g., "Trace"). Tell the user to press Cmd+Shift+R (hard refresh) or open in a private window. Verify the new tab exists by curling the page and grepping for the tab id.
- **Board routing with --board flag**: The `--board` flag for `hermes kanban` must go AFTER `kanban` and BEFORE the subcommand: `hermes kanban --board <slug> create ...`. Putting it at the end (`hermes kanban create ... --board <slug>`) silently fails — tasks land on the wrong board with no error.
- **boards create --switch doesn't actually switch**: `hermes kanban boards create <slug> --switch` creates the board but does NOT change the current board for subsequent `kanban create` calls. Always explicitly run `hermes kanban boards switch <slug>` before creating tasks.
- **Trace data in /api/all freezes the browser**: Including trace data (expensive JOINs across all board DBs) in `/api/all` (polled every 5 seconds) will freeze the browser. Keep trace data in a separate `/api/trace` endpoint that only loads when the user clicks the Trace tab.
- **Multi-line JSON from kanban create**: `hermes kanban create --json` outputs status lines followed by a multi-line JSON block. Parse by finding `\n{` and parsing from there, NOT by looking for any line starting with `{`.
- **Dashboard subprocess python path**: When the dashboard server spawns subprocesses (innovator.py, etc.), use `sys.executable` not `"python3"`. The dashboard runs under launchd which has a minimal PATH — `python3` may not resolve.
- **launchd PATH**: The dashboard runs under launchd which does NOT have `hermes` in PATH. Always use the absolute path `/Users/kamarulhk/.local/bin/hermes` in server code, not bare `hermes`.
- **Kanban events table**: The table is `task_events` (columns: `task_id`, `run_id`, `kind`, `payload`, `created_at`), NOT `events`. Querying `events` will crash the dashboard.
- **Reassign running tasks**: `hermes kanban reassign` fails on running tasks. Call `hermes kanban reclaim <task-id>` first to release the lock.
- **MCP add prompt**: `hermes mcp add` interactively asks "Enable all N tools?". Pipe `echo "Y"` to auto-accept, or the command hangs.
- **Chat timeout**: `hermes chat -q` spawns a full agent session (30-120s). For dashboard chat, use `subprocess.Popen` with `start_new_session=True` for fire-and-forget, and show responses in the Thinking tab instead of waiting.
- **File filter with relative paths**: When filtering hidden files in workspace directories, use `f.relative_to(base_dir).parts` NOT `f.parts`. The full path includes `.hermes` which starts with a dot, causing ALL files to be filtered out and returning empty results.
- **Workspace garbage collection**: Completed task workspaces are garbage-collected and moved to `~/.hermes/kanban/attachments/<task_id>/`. Always check both `workspaces/` and `attachments/` directories when looking for task deliverables.
- **Dashboard function scope**: When adding new API endpoints to the dashboard server, define handler functions at module level (not as methods on the request handler class). A `NameError` occurs if a method references a function defined inside another method.
- **Config key warnings**: `hermes config set` with unrecognized keys (like `skills.auto_load`) still saves the value but prints a warning. This is harmless — the value is persisted.
- **Profile model config**: Set `model.provider` and `model.default` (not `provider` and `default` at top level). The top-level keys are not read by Hermes.

## Discussion Room

A kanban-style discussion board where multiple agents with different personas and LLM models debate topics. Built into the dashboard at the "Discussion Room" tab.

### Architecture

- **Discussion DB**: `~/.hermes/discussion-room.db` (SQLite) with `topics` and `comments` tables
- **Persona Library**: `~/.hermes/persona-library/personas.json` — 200+ generated personas with archetype, domain, alignment, traits, experience level
- **Persona State**: Each profile has `~/.hermes/profiles/<name>/personas/active_persona` pointing to the active persona ID
- **Avatars**: `~/.hermes/avatars/<name>.png` — cat-themed avatars per agent, served at `/api/avatar/<name>`
- **Model Config**: Per-profile `config.yaml` with `model.provider` and `model.default` — switchable via API

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/personas` | List all 200 personas |
| GET | `/api/persona/active?profile=<name>` | Get active persona for a profile |
| POST | `/api/persona/set` | Set active persona `{profile, persona_id}` |
| GET | `/api/discussion/list` | List all topics with comments |
| POST | `/api/discussion/create` | Create topic `{title, topic, author}` |
| POST | `/api/discussion/post` | Post comment `{topic_id, author, body}` |
| GET | `/api/models` | List available LLMs grouped by provider |
| POST | `/api/model/set` | Set model for profile `{profile, provider, model}` |
| GET | `/api/avatars` | List avatar paths per agent |
| GET | `/api/avatar/<name>` | Serve avatar PNG (auto-appends `.png` if missing) |

### Discussion Flow

The discuss system is **manual-wake**: agents stay asleep until the user clicks "Discuss". When woken, they read the full topic + all previous comments, then post a fresh response. They do NOT auto-wake when the user replies — the user must click "Discuss" again to call them back. This is by design (MARU confirmed: "maintain as is").

**Round tracking**: Each discuss call increments a `round_num` stored in the comments table. The frontend groups comments by round with visual labels (Round 1, Round 2, etc.) so the conversation evolution is visible.

**Auto-refresh during discussion**: When "Discuss" is clicked, the frontend starts a `setInterval` polling `/api/discussion/list` every 5 seconds. This pulls in new agent replies automatically without manual refresh. The interval clears when the discuss POST completes.

**"Discussing..." badge**: While agents are working, a blue pulsing badge appears next to the topic title. The badge is controlled by comparing `activeRound[topicId]` against the max `round_num` in the comments.

**Stop button**: Kills all running `subprocess.Popen` processes, clears all auto-refresh intervals, re-enables all discuss buttons, removes the "Discussing..." badge, and refreshes the topic list. Uses a global `running_discuss_procs` list to track Popen objects.

### Persona System

Personas are generated combinatorially from:
- **20 Archetypes**: Leader, Creator, Analyst, Rebel, Mentor, Visionary, Strategist, Critic, Builder, Explorer, Guardian, Trickster, Healer, Warrior, Sage, Innovator, Diplomat, Perfectionist, Minimalist, Chaos Agent
- **10 Domains**: Technology, Business, Design, Science, Psychology, Philosophy, Marketing, Finance, Engineering, Arts
- **4 Alignments**: Good (supportive), Neutral (balanced), Chaotic (devil's advocate), Mixture (custom blend)
- **30 Traits**: Pragmatic, Creative, Data-Driven, Empathetic, Analytical, Intuitive, Systematic, Spontaneous, Detail-Oriented, Big-Picture, Risk-Averse, Risk-Taking, Patient, Impatient, Diplomatic, Blunt, Humorous, Serious, Optimistic, Pessimistic, Collaborative, Independent, Methodical, Flexible, Stubborn, Curious, Cautious, Bold, Reflective, Action-Oriented
- **4 Experience Levels**: Novice, Intermediate, Expert, Master

Each persona has a `soul` field — the system prompt text injected into the agent's context. Personas are switchable at runtime via the dashboard dropdown.

### Model Switching

Each agent profile can use a different LLM. The dashboard renders a per-agent `<select>` dropdown populated from `/api/models`. On change, it POSTs to `/api/model/set` which rewrites the profile's `config.yaml` `model.provider` and `model.default` fields in place.

Available providers: Nous (free Longcat), OpenAI (GPT-4o, GPT-4o-mini, GPT-3.5), Google (Gemini 2.5 Flash/Pro, 2.0 Flash), Anthropic (Claude Sonnet 4, 3.5 Sonnet, 3 Haiku), Mistral (Large, Small), DeepSeek (Chat, Reasoner).

### Agent Roster

| Profile | Name | Role | Avatar |
|---------|------|------|--------|
| default | Neo | CEO / Pragmatist | Black cat with bowtie |
| max | Max | Architect / Engineer | Tabby with goggles |
| lisa | Lisa | Designer / User Advocate | Calico with scarf |
| genny | Genny | Researcher / Fact-Checker | Siamese with magnifying glass |

### Avatar Sizes

MARU explicitly requested LARGE visible avatars ("way bigger, i wanna see the cat face"). Current sizes:
- Agent persona cards: **120px** circular, 3px purple border (`#8b5cf6`)
- Model switcher: **64px** circular, 2px gray border
- Comment avatars: **56px** circular, 2px purple border

If MARU asks for bigger avatars again, increase proportionally — minimum is 120px for primary display.

### Devil's Advocate Preset

One-click persona for maximum challenge — agent's entire job is to tear apart the idea, find flaws, argue the opposite. Select "Chaotic" alignment in the persona picker to activate. MARU specifically requested this as a preset rather than requiring manual trait configuration.

### Pitfalls

- **Avatar route**: The `/api/avatar/<name>` handler must auto-append `.png` if the URL doesn't include it — browsers request `/api/avatar/neo` not `/api/avatar/neo.png`.
- **Query string parsing**: `urlparse().query` returns a string, not a dict. Use `urllib.parse.parse_qs()` to extract parameters from API URLs.
- **Profile list**: The `get_profile_configs()` function must iterate over the actual profile names (`default`, `max`, `lisa`, `genny`) — not stale names like `neo`.
- **Discussion DB init**: Call `init_discussion_db()` before any read/write to ensure tables exist. The function is idempotent.
- **Model config rewrite**: When setting a model via API, the `set_profile_model()` function must handle the case where `model.provider` or `model.default` lines don't exist yet in config.yaml — it appends them if missing.
- **Button debounce for POST handlers**: Any dashboard button that triggers a POST request must disable itself immediately on click, show a loading state ("Posting..."), and re-enable only after the `fetch()` completes (in a `finally` block). Without this, rapid clicks create duplicate records — a user testing the UI by clicking multiple times will fill the DB with duplicates.
- **SQLite date format for JS**: SQLite `datetime('now')` returns `YYYY-MM-DD HH:MM:SS` which JS `new Date()` cannot parse (returns Invalid Date). Before sending dates to the frontend, convert: `dt.replace(' ', 'T') + 'Z'`. The JS `formatTime` helper should also guard with `isNaN(d.getTime())` and return the raw string as fallback.
- **launchd restart**: The dashboard runs under launchd with `KeepAlive=true`. `pkill -f "team-dashboard/server.py"` kills the process but launchd immediately respawns it with the OLD code. To pick up code changes: `launchctl unload ~/Library/LaunchAgents/ai.hermes.team-dashboard.plist` then `launchctl load ~/Library/LaunchAgents/ai.hermes.team-dashboard.plist`. Only `server.py`
  needs this — the RE bridge is spawned per request, so bridge edits are live on the next run
  with no restart at all.
- **ThreadingHTTPServer is mandatory**: The dashboard MUST use `ThreadingHTTPServer` (from `socketserver import ThreadingMixIn`), not plain `HTTPServer`. When the discuss endpoint spawns `subprocess.run` to wake agents (30-120s each), a single-threaded server blocks ALL other requests — the browser shows "Failed to fetch" and the UI freezes. With `ThreadingHTTPServer(daemon_threads=True)`, the server stays responsive while agents work in background threads.
- **hermes chat flags**: Use `--oneshot` (not `--no-tools` which doesn't exist) for one-shot queries. Use `--query-file <path>` instead of `-q` for long prompts with special characters — `-q` can mangle quotes/backticks. Add `-Q` for quiet mode to reduce output noise. The output includes a `Query: ...` echo prefix that must be stripped before saving to DB.
- **Local import shadowing in do_POST**: Never use `from urllib.parse import urlparse` inside a method body when `urlparse` is already imported at module level — Python treats it as a local variable, causing `UnboundLocalError`. Use the module-level import directly, or use different local names.
- **DB schema migration**: When adding columns to existing SQLite tables, use `try/except sqlite3.OperationalError` with `ALTER TABLE ... ADD COLUMN` — the `CREATE TABLE IF NOT EXISTS` won't add columns to an existing table. The `round_num` column was added this way after the initial schema was already deployed.
- **Stop button must clear ALL state**: The stop handler must: (1) kill running subprocesses, (2) clear all `setInterval` auto-refresh timers, (3) delete all `activeRound` entries, (4) re-enable all discuss buttons, (5) refresh the topic list to remove "Discussing..." badges. Missing any of these leaves the UI in a broken state.
- **Discuss endpoint method**: The frontend sends POST with query params (`?topic_id=X&round=Y`). The handler must parse query string via `parse_qs(urlparse(self.path).query)` and accept the parsed dict, NOT the raw `ParseResult` object.

## Reviewing a teammate profile's change

Other profiles (Max, Lisa, Genny) edit the same shared files you do — dashboard, bridge
scripts, repos. When the founder says "X did something, take a look", review it as a change,
not as a fresh problem:

1. **Find the change, do not guess.** `ls -laT <dir>` for mtimes, then diff against the sibling
   `.bak` / `.bak-<stamp>` files that get left behind: `diff <file>.bak <file>`. A file
   modified minutes apart from its backup is the change.
2. **Confirm it is actually live.** The dashboard runs under launchd `KeepAlive`, so an edit
   does not take effect until the process restarts. Compare process start time to file mtime:
   `ps -o pid,lstart,command -p <pid>`. Process started *after* the edit ⇒ live; before ⇒ the
   founder is looking at stale behaviour.
3. **Probe the live surface** rather than reading code and assuming: `curl` the endpoint the
   change adds and check status *and* content-type.
4. **Attribute it before crediting anyone.** The teammate's own summary is in its session
   store: `sqlite3 ~/.hermes/profiles/<name>/state.db "SELECT substr(content,1,300) FROM
   messages WHERE content LIKE '%<keyword>%' ORDER BY id DESC LIMIT 5;"`. Team memory
   (`~/.hermes/team-memory.db`) may not carry it — absence there is not absence of work.
5. **Report verified and gap separately.** State which fixes you reproduced, then what the fix
   still does not cover. Passing validation is not correct output: a change can make an input
   get accepted while the analysis still runs on the wrong architecture and the number shown to
   the user is still wrong. Follow the whole path to the value the founder actually sees.

## Team Memory Integration

All profiles share a team memory database at `~/.hermes/team-memory.db` (SQLite + FTS5). Use the `team-memory` skill to log and search cross-profile memories. The dashboard reads this DB to show what the team remembers.

## Cron Jobs

Schedule recurring team tasks with `cronjob_manage`:

```
action: create
schedule: "every monday 9am"
name: "Weekly Security Audit"
prompt: "You are Neo, CEO of the Hermes agent team. Coordinate a full security audit..."
deliver: origin
skills: ["team-memory"]
```

The cron job runs in a fresh session with no chat context — prompts must be self-contained.
