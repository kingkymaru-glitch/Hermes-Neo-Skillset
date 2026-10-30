---
name: macos-desktop-launcher
description: "Fix macOS .command launchers that fail when double-clicked."
version: 1.0.0
---

# macOS Desktop `.command` Launcher

## Trigger / When to use
User asks for a Desktop button/launcher, ".command does nothing", "double-click did
nothing", "make a launcher that starts the server and opens the browser". Covers
launching a local webapp (Flask, Node, Vite, Python) from the macOS Desktop.

Also fires when the user asks to **change the icon of a desktop button**, or wants the app
to open with **no Terminal window**. Both mean leave `.command` behind and build a `.app`
bundle — a `.command` is a shell script and Finder gives it the generic Terminal document
icon with no supported way to attach a custom one. Recipe: `references/app-bundle.md`.

Pick the target first: `.command` for a throwaway/terminal-only launcher, `.app` bundle for
anything the user sees as an app (icon, no Terminal, single Dock entry).

## The core pitfall
A `.command` file runs fine from the terminal but FAILS SILENTLY when double-clicked,
because macOS opens it via `open` with a BARE GUI environment: no shell rc, no user
`PATH`, and **`python3` does NOT see user site-packages**
(`~/Library/Python/X.Y/lib/python/site-packages`). Result: `ModuleNotFoundError:
No module named 'flask'` — logged to the script's own log, nothing on screen.

## The fix (apply ALWAYS for Python launchers)
Pin `PYTHONPATH` and `PATH` at the top, BEFORE launching the app:
```bash
DIR="$HOME/Desktop/crypto_bot/live_1m"
export PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
PYBIN="/usr/bin/python3"
nohup "$PYBIN" "$DIR/app.py" > "$DIR/launch.log" 2>&1 &
```
- Use `/usr/bin/python3` (sees user site-packages once PYTHONPATH is set). Never bare `python3`.
- Version dir from `python3 --version` on the Mac (seen 3.9.6 → `Python/3.9`).

## Minimal robust template
```bash
#!/bin/bash
DIR="$HOME/Desktop/<appdir>"
LOG="$DIR/launch.log"
PORT=5055
cd "$DIR" || exit 1
export PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
pkill -f "<appdir>/app.py" 2>/dev/null || true
sleep 1
nohup /usr/bin/python3 "$DIR/app.py" > "$LOG" 2>&1 &
for i in $(seq 1 40); do
  if curl -s -o /dev/null "http://127.0.0.1:$PORT/"; then
    open "http://localhost:$PORT"; exit 0
  fi
  sleep 0.5
done
open "http://localhost:$PORT"
```

## Pitfalls
1. Silent failure under `open` — always add PYTHONPATH/PATH export.
2. `pkill` with spaces: `pkill -f "python3 $DIR/app.py"` never matches (DIR has a space).
   Match the directory marker: `pkill -f "crypto_bot/live_1m/app.py"`.
3. Gatekeeper: first double-click may prompt "unidentified developer" — normal, click Open.
4. `chmod +x` the file or Finder won't run it.
5. If the host is DNS-blocked, override DNS in-process (see `live-feed-debug`).
6. **Read the bundle version from the app's own version constant — never hardcode it in the
   build script.** A literal in the script drifts the first time someone bumps the package
   and forgets the second place, and the plist then *confidently* disagrees with the code it
   contains. One command in the script keeps them locked:
   `VERSION="$(.venv/bin/python -c 'import sys; sys.path.insert(0,"src"); import pkg; print(pkg.__version__.lstrip("Vv"))')"`
   then strip any descriptive suffix (`VERSION="${VERSION%%-*}"`) because macOS wants a
   dotted numeric version. Verify after building:
   `plutil -p "$APP/Contents/Info.plist" | grep ShortVersion`.

## Verify with the REAL mechanism (not terminal)
```bash
open /Users/kamarulhk/Desktop/launch_<x>.command   # simulates double-click
sleep 6
curl -s -m5 -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:<PORT>/
grep -i "ModuleNotFound\|Traceback" "$DIR/launch.log" || echo "clean boot"
```
`open` starts it and the port answers with no ModuleNotFound = the Desktop button works.

## See also
- `references/app-bundle.md` — `.app` bundle recipe: Info.plist keys, the `.icns`
  `iconset`+`iconutil` build, drawing an icon that reads at 16px, the `exec`-vs-child Dock
  icon trap, Launch Services icon caching, and the verification checklist.
- `software-development:live-feed-debug` — cause #4 (DNS sinkhole) for feed-connect failures.
- `gepeto` — Pinokio 1-click launchers (different mechanism).
- `templates/launch_command.sh` — copy-paste starter launcher (edit DIR/PORT/APP).
