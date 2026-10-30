---
name: macos-desktop-launchers
description: Build macOS .command launchers for local Python servers.
---

# macOS Desktop Launchers for Local Apps

## When to use
The user wants a "button on the desktop" to launch a local app/server (Flask, FastAPI,
Streamlit, any `python app.py`). Deliver a `.command` file on `~/Desktop`. Double-click runs it.

**First question: does it need a custom icon?** A `.command` is a shell script — Finder gives it
the generic Terminal document icon and there is **no supported way to attach a custom one**
(resource-fork `Rez`/`SetFile` hacks are gone from modern macOS; `fileicon` is not installed by
default). The moment the user asks for a specific icon on that button, stop building a `.command`
and build an `.app` bundle instead — it also opens without dropping the user into a Terminal.

## The executable MUST be a Mach-O, not a shell script

A `.app` whose `CFBundleExecutable` is a bash script is broken in three ways at
once, and all three present identically: **you double-click and nothing happens.**

1. **Architecture.** With no Mach-O to read, the launch context can come up
   x86_64 under Rosetta. arm64 wheels then fail to dlopen with
   `incompatible architecture (have 'arm64', need 'x86_64')` — while the same
   import succeeds from your terminal. This looks like a broken venv; it is not.
2. **Codesign.** `codesign` on a script bundle yields something macOS then
   refuses to launch at all — `open` returns 0, no process, no log.
3. **TCC.** A bare script has no bundle identity to attach a permission grant to.

Ship a compiled stub that hands off to the shell script:

```
Contents/MacOS/MyApp          cc -O2 -arch arm64 -o ... launch_stub.c   (Mach-O)
Contents/Resources/launch.sh  the real logic, copied in as a file
```

The stub uses `_NSGetExecutablePath`, takes `dirname` twice to reach `Contents`,
and `execl("/bin/bash", "bash", "<Contents>/Resources/launch.sh")`.
Verify with `file` — it must report `Mach-O 64-bit executable arm64`.

### Sign it, or tccd denies the launch

A Mach-O that is merely *unsigned* still fails, and fails silently — the app dies
before any of your own code runs, so **not even the log line appears**:

```
tccd: failed to read header from .../Contents/MacOS/MyApp: truncated
```

Fix with an ad-hoc signature. It needs no certificate and no developer account:

```bash
codesign --force --sign - --identifier com.you.myapp "$APP"
codesign --verify --verbose=2 "$APP"   # expect: valid on disk
```

This is why "it cannot start" with an empty log is a *signing* symptom, not a
script bug: the failure happens above your code. Check
`log show --last 5m --predicate 'eventMessage CONTAINS[c] "MyApp"'` for tccd
lines before debugging the launcher itself. Confirm the GUI really came up with
`osascript -e 'tell application "System Events" to count windows of (first
process whose name is "Python")'` — a running PID is not a visible window.

## Generate launch.sh as a FILE, never a heredoc

Writing the launcher with `cat > … <<LAUNCHER` silently mangles it: every runtime
variable must be escaped, and with `set -u` an unescaped `$1` or `$PID` aborts the
build with `unbound variable` (a comment mentioning `$1` is enough to trigger it).
Keep the script as a real file in the repo and `cp` it into the bundle.

## A pgrep guard cannot match a venv python

macOS resolves `.venv/bin/python` to the framework interpreter, so the child's
argv reads `…/Python.app/Contents/MacOS/Python -m app` and **never contains the
venv path**. Any pattern matching the venv silently never matches, so every
double-click starts another copy fighting over the same output directory.

Guard with a PID file instead: write `$!` on start, `kill -0` it on the next
launch, and `trap 'rm -f "$PIDFILE"' EXIT` so a normal quit does not leave a
stale lock that blocks the next start.

## TCC: keep the repo out of ~/Documents

A Finder-launched app cannot read `~/Documents`, `~/Desktop` or `~/Downloads`
without a grant, and a local build never has one. It fails with
`PermissionError: [Errno 1] Operation not permitted` on the first file it reads —
for a venv, `pyvenv.cfg`. Your terminal HAS the grant, which is exactly why every
direct run works and only the double-click fails.

Fix by keeping the project directly in `$HOME` (e.g. `~/MyApp`, alongside the
user's other repos). A venv survives a same-volume move: `pyvenv.cfg` records the
base interpreter, not its own path. Repoint any absolute path in your build
scripts afterwards.

## Stale LaunchServices entries break `open`

Symptom: `open` returns 0 with no process, or
`_LSOpenURLsWithCompletionHandler() failed with error -1712` (a timeout). Cause is
usually several bundles sharing a name — deleted ones in `~/.Trash`, old build
output under `dist/`, an earlier path. Audit and re-register:

```bash
lsregister -dump | grep -i "myapp.app"          # find the competing entries
lsregister -f "/path/to/MyApp.app"              # force re-register the right one
```

Give your bundle a distinct `CFBundleIdentifier` too, so it cannot be confused
with a pre-existing build of the same app.

## Custom icon ⇒ build an .app bundle

```
MyApp.app/Contents/
  Info.plist              CFBundleExecutable=launcher, CFBundleIconFile=appicon, CFBundlePackageType=APPL
  MacOS/launcher          the bash launcher, chmod +x
  Resources/appicon.icns  the icon   (+ appicon.png 1024px if the app sets a window icon)
```

Three things that are easy to get wrong:

- **Do NOT `exec` the app process — run it as a child and wait.** `exec python -m app` replaces the
  process image, so macOS associates the running app with the *framework* interpreter and the Dock
  shows that interpreter's icon instead of the bundle's. Staying alive as the parent keeps the
  bundle identity. The Finder/desktop icon comes from `CFBundleIconFile` either way.
- **Re-register with Launch Services after building**, or Finder keeps showing the old/generic icon:
  `touch "$APP"` then
  `/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP"`.
- **A Finder launch has no terminal.** Redirect output to `~/Library/Logs/<app>.log` and surface a
  failure with `/usr/bin/osascript -e 'display alert "…" message "…"'` — otherwise a crash is
  completely silent and reads as "nothing happened".

Icon build: draw at 1024 and downsample (supersample the glyph, and mask-composite rounded corners
rather than overdrawing, so edges stay clean). `iconutil -c icns appicon.iconset -o appicon.icns`
requires these exact ten names, or sizes get silently dropped:
`icon_16x16.png icon_16x16@2x.png icon_32x32.png icon_32x32@2x.png icon_128x128.png
icon_128x128@2x.png icon_256x256.png icon_256x256@2x.png icon_512x512.png icon_512x512@2x.png`.
Design ONE bold shape — the icon is read at 16px in the Dock and the Finder list.
Verify by round-trip: `iconutil -c iconset appicon.icns -o /tmp/check` and confirm all ten files come
back; compare the bundled `.icns` md5 against the generated one. A locally built bundle carries no
quarantine attribute, so it launches without a Gatekeeper prompt.

Expose the whole thing as two re-runnable scripts in the repo (`make_app_icon.py` and
`build_macos_app.sh`) so the icon shade or the bundle can be re-cut in seconds on request — the user
will often want a different colour once they see it.

## Core pattern (see scripts/launcher_template.command)
1. `cd` into the app dir via `$HOME/...` absolute paths — never rely on cwd.
2. Pin the Python environment — CRITICAL (see Pitfalls).
3. Kill any prior instance on the port using a directory-marker pkill pattern.
4. `nohup "$PYBIN" app.py > log 2>&1 &` (background; survives script exit).
5. Poll the port with curl; once up, `open http://localhost:PORT`.
6. `exit 0` so the Terminal window closes (less intrusive). `chmod +x` the file.

## Pitfalls (all learned the hard way this session)
- **GUI launch drops user site-packages from PATH.** Double-clicking a `.command` runs via
  Finder with a minimal environment; `/usr/bin/python3` lacks pip-installed packages (flask,
  flask-socketio, etc.) even though they live in `~/Library/Python/3.9`. Symptom: silent
  `ModuleNotFoundError` in the log, "nothing happens" on screen. FIX: at the top of the
  launcher `export PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"`
  and `export PATH="$HOME/Library/Python/3.9/bin:$PATH"`. This is the #1 reason "I clicked it
  and nothing happened." Verify the bin that has the deps with `python3 -c "import flask"`.
- **pkill pattern with spaces breaks.** `pkill -f "python3 $DIR/app.py"` fails when `$DIR`
  contains a space (e.g. `Desktop/crypto_bot`) — the pattern never matches, so a stale server
  keeps the port. Use a stable directory marker: `pkill -f "crypto_bot/live_1m/app.py"`.
- **Bind address for LAN reachability.** If another device (phone, S22) must reach the server,
  the app must `app.run(host="0.0.0.0", ...)`. `127.0.0.1` allows localhost only. See
  references/lan_device_streaming.md.
- **Local DNS sinkhole.** Some hostnames (e.g. Bybit) resolve via local DNS to a dead IP while
the public resolver returns a live one. Pin the address with `socket.getaddrinfo` rather than
trusting the system resolver. See references/dns_sinkhole_bypass.md.

## Support files in this skill
- `scripts/launcher_template.command` — copy/paste launcher skeleton (fill DIR/PORT/PYBIN/marker).
- `references/lan_device_streaming.md` — phone/S22 LAN streaming "nothing connects" debug.
- `references/dns_sinkhole_bypass.md` — local DNS sinkhole (e.g. Bybit) → socket.getaddrinfo pin.

## Menu bar indicator (.app bundle)

For long-running local servers, a menu bar indicator is more usable than a terminal window.
Build a Swift `.app` bundle that polls the server and shows live status.

**Pattern (tested with CDM's worker launcher):**

1. Write `indicator.swift` — an `NSApplication` with `.accessory` activation policy (no dock icon),
   an `NSStatusItem` with a menu, and a `Timer` that polls every 5s.
2. **Compile:** `swiftc -o "MyApp" indicator.swift -framework AppKit -framework Foundation`
3. **Bundle:** `mkdir -p "MyApp.app/Contents/MacOS" && cp MyApp "MyApp.app/Contents/MacOS/"`
4. **Add `Info.plist`** with `LSUIElement` set to `true` (hides from dock) and `CFBundleIconFile`
   pointing to an `.icns` in `Contents/Resources/`.
5. **Generate icon:** Python Pillow → `icon.png`, then `iconutil -c icns icon.iconset` → `icon.icns`.

**The launcher `.command` starts the server + opens the indicator `.app`:**
```bash
nohup node server.js > log 2>&1 &
sleep 2
open "$HOME/Desktop/MyApp.app"
```

**Status check via `pgrep`** (Swift `Process` running `/usr/bin/pgrep -f <pattern>`). Parse the
output — empty means stopped, non-empty means running. Update the menu bar title and menu items
on each poll tick.

**Menu items to include:** status lines, per-service status (if multiple), "Open app…" (launches
the web URL), "Quit" (calls `NSApplication.shared.terminate`).

### View-only or a control surface? ASK, and default to control
An indicator can be a pure read-out or a real control surface that starts and stops the
processes. Do not assume read-out: a user who wants to start the tunnel and the server from
the menu bar is asking for controls, and shipping them a status lamp reads as a broken app.
Build the control surface and include, at minimum: start, restart-one-service, stop-one-service,
stop-everything (with confirmation), open, copy-the-current-URL, open-the-log.

### Swift menu bar app — the five defects that make every button dead
These all present identically to the user: **the menu opens, the items highlight, nothing
happens.** Check every one before concluding the build is fine.

1. **`NSMenuItem(title:action:keyEquivalent:)` leaves `target` nil.** The action is then
dispatched up the responder chain, which in a windowless `.accessory` app does not reliably
reach the delegate. **Set `item.target = self` on EVERY actionable item.** This is the single
most common cause of a dead menu bar menu.
2. **The delegate must declare conformance**: `class D: NSObject, NSApplicationDelegate`.
A bare `NSObject` with a method that merely *looks* like `applicationDidFinishLaunching` may
never be called.
3. **Never do blocking work in the Timer callback.** `Process.waitUntilExit()` and
`CFSocketConnectToAddress` with a 2 s timeout both run on the main run loop, so a 5 s poll
makes the menu bar genuinely unresponsive for up to 2 s at a time — the other half of "I can't
click any of it". Probe on a `DispatchQueue(label:qos:.utility)` and hop back to main only to
set labels.
4. **A stale `pgrep` pattern silently reports a healthy service as down.** The moment a launch
command gains a flag (`cloudflared tunnel --url` -> `cloudflared tunnel --edge-ip-version 4
--url`), the old pattern stops matching. Match the *stable* prefix (`cloudflared tunnel`), and
prefer checking the real signal (log contains a registration, port answers) over process
existence.
5. **No feedback makes a working button and a dead one indistinguishable.** Write a
"last: …" line into the menu before and after every action, and log to a file — a menu bar app
has nowhere to print, so without `~/…/<app>.log` the question "did my click do anything?" is
unanswerable after the fact.

### Other rules for a control surface
- **Guard against a second instance.** Two copies polling and each able to kill processes makes
the menu ambiguous. Take an `flock(LOCK_EX|LOCK_NB)` on a lock file; the kernel releases it on
process death, so a crash cannot leave a lock blocking the next launch.
- **Confirm destructive actions.** Killing a running demo on one mis-click is not acceptable;
`NSAlert` with a Cancel button, and say in the confirm text what the user will lose.
- **Do not kill and restart blind.** If you restart a tunnel or server, wait for a real readiness
signal (registration line in the log / port answering), not just for the process to exist, then
re-assert any downstream pointer (a DB row holding the URL) so nothing keeps calling the old
address.
- **`app.setActivationPolicy(.accessory)`** for menu-bar-only; call
`NSApp.activate(ignoringOtherApps: true)` before showing an `NSAlert`, or the modal can appear
behind other windows.

### Build + install recipe
```bash
xcrun swiftc -O -wmo -o MyApp main.swift            # -wmo needs a single file or whole-module setup
mkdir -p "$HOME/Desktop/MyApp.app/Contents/MacOS" "$HOME/Desktop/MyApp.app/Contents/Resources"
cp MyApp "$HOME/Desktop/MyApp.app/Contents/MacOS/"
# Info.plist: CFBundleExecutable, CFBundleIdentifier, LSUIElement=true, CFBundleIconFile
codesign --force --deep --sign - "$HOME/Desktop/MyApp.app"   # ad-hoc, avoids quarantine
plutil -lint "$HOME/Desktop/MyApp.app/Contents/Info.plist"
```
Kill any older copy by PID before launching the new one, and confirm exactly one instance runs.
**Name the bundle after what it CONTROLS, not the project it was born in** — a menu bar app
inheriting a legacy project name while driving a different product's server is a support burden
(the user will ask "is this X or Y?").

## Verify (simulate the double-click)
`open /path/to/launcher.command` then
`curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:PORT/` → expect 200.
Tail the launcher log for `ModuleNotFoundError` / `Address already in use` / `Traceback`.
