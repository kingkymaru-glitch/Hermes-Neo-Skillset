---
name: hermes-sibling-agent-spawn
description: Spawn a sibling Hermes agent profile (LISA) and launch it.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hermes, profiles, multi-agent, spawning, tmux]
    related_skills: [hermes-agent, computer-use]
---

# Spawning a Sibling Hermes Agent

Use when the founder (MARU) asks to create another Hermes agent — e.g. "create
another hermes agent with similar skills and mindset, name it LISA and launch
it." A sibling agent is a separate **profile** with the same skill set and
working style, dedicated to a project.

## Core workflow

1. **Create the profile by cloning the active one** so it inherits skills,
   config, model, and memory baseline:
   ```
   hermes profile create <name> --clone-all \
     --description "<one-two sentence role + project focus for the kanban decomposer>"
   ```
   - `--clone-all` copies config.yaml, .env, SOUL.md, skills, and memories.
   - Creates a CLI wrapper: `~/.local/bin/<name>` (so `<name>` runs the agent
     from any shell). Verify with `which <name>`.

2. **Rewrite SOUL.md** with the new identity + mindset. Pattern (see the real
   LISA file at `~/.hermes/profiles/lisa/SOUL.md`):
   - Self-identify as the new name ("you are LISA").
   - Founder = MARU; state the assigned project + its repo.
   - Copy the founder-collab mindset block: terse, decisions+clarifications
     only, no thinking-narration (ADHD-aware), discovery-first facts-before-
     code, confirm destructive actions, make cross-links LIVE not code-present,
     never fabricate results.
   - Write to `<profile>/SOUL.md` (not the default profile's).

3. **Seed memory** with the durable project context so it starts oriented:
   project identity, repo URL + privacy, mindset rules. Write to
   `<profile>/memories/MEMORY.md`.

   NOTE: writing into another profile's dir triggers Hermes' cross-profile soft
   guard. The founder explicitly ordered this agent's creation, so pass
   `cross_profile=true` on the write_file to bypass (defense-in-depth only).

4. **Verify it actually works** before launching:
   ```
   lisa chat -q "Who are you? Reply in one sentence only."
   ```
   Confirm it self-identifies with the new name and references its project.
   - macOS has NO `timeout` binary — do NOT prefix with `timeout 60`. Run the
     command directly (it self-terminates) and rely on the tool timeout.

5. **Launch it interactively** in tmux so it's live and attachable:
   ```
   tmux kill-session -t lisa 2>/dev/null
   tmux new-session -d -s lisa -x 160 -y 48 'lisa'
   sleep 6 && tmux capture-pane -t lisa -p | tail -15
   ```
   Expect the `lisa ❯` prompt. Tell the founder to attach with
   `tmux attach -t lisa` or just run `lisa` anywhere.

## Relaying a question to a live sibling (host-agent → sibling)

When the founder types a question addressed to the sibling into YOUR session
("lisa, where is the html?"), don't just answer it yourself — relay it into the
sibling's tmux session and bring back its answer, so the agent that owns the
project responds:

```
# send the question, then wait for the sibling to work
tmux send-keys -t lisa 'where is the html?' Enter
sleep 25 && tmux capture-pane -t lisa -p | tail -30
```

- The first capture often shows the sibling still mid-task (searching files /
  building context). Capture again after another `sleep` to get the final answer.
- A full-disk `find /Users/kamarulhk -iname "*.html"` from the sibling can time
  out (exit 124) on a large home dir. If the host agent knows the repo location,
  short-circuit: relay the answer to the sibling yourself so it re-orients on the
  real path instead of burning minutes searching.
- **Empty-repo gotcha:** the skill's `gh api .../git/trees/<branch>` shortcut
  returns `409 "Git Repository is empty"` when the repo exists on GitHub but has
  NO commits yet — even though a local working copy is fully populated and
  unpushed. When a relayed question is "where is the code/file?", the host MUST
  check the LOCAL clone first:
  ```bash
  ls -d /Users/kamarulhk/<repo> 2>/dev/null && cd /Users/kamarulhk/<repo> \
    && git status && git ls-files | head
  ```
  If the local dir has the files, hand the sibling the exact absolute path
  (`/Users/kamarulhk/ERP-PILOT/index.html`) rather than letting `gh` mislead it.
  Only trust `gh api .../git/trees` once you've confirmed the branch has commits
  (e.g. `gh api repos/<owner>/<repo>/commits` returns a list).

## Pitfalls
- `hermes profile create` clones from the **active** profile, not necessarily
  `default` — verify the result with `hermes profile list` (LISA cloned from
  `smith`, which already carried the founder-mindset skills).
- A sibling agent is long-running/independent (hours-days), unlike
  `delegate_task` (minutes, shared process). Use tmux + full tool access, not
  delegation, for these.
- Give the new agent its OWN project focus in SOUL/memory so it isn't a
  duplicate persona — it should route to its assigned repo, not Neo's.
