# macOS `.app` bundle launcher — custom icon, no Terminal window

## When to use
Choose a bundle over a `.command` when EITHER holds:

- **The user asks to change the Desktop button's icon.** A `.command` is a shell script,
  so Finder gives it the generic Terminal document icon and there is **no supported way to
  attach a custom one**. "Change the icon" is a request to move to a bundle.
- The app should open with **no Terminal window** (a GUI app, or a background service).

A `.command` remains correct for a throwaway/terminal-only launcher. Keep one in the repo as
an explicit fallback when you build the bundle.

## Build recipe

```bash
APP="$HOME/Desktop/My App.app"
rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# 1. executable  (same PATH/PYTHONPATH exports a .command needs — see SKILL.md)
cat > "$APP/Contents/MacOS/launcher" <<'SCRIPT'
#!/bin/bash
# ...body...
SCRIPT
chmod +x "$APP/Contents/MacOS/launcher"

# 2. Info.plist
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
 <key>CFBundleName</key><string>My App</string>
 <key>CFBundleDisplayName</key><string>My App</string>
 <key>CFBundleExecutable</key><string>launcher</string>
 <key>CFBundleIconFile</key><string>appicon</string>
 <key>CFBundleIconName</key><string>appicon</string>
 <key>CFBundleIdentifier</key><string>com.example.myapp</string>
 <key>CFBundlePackageType</key><string>APPL</string>
 <key>CFBundleShortVersionString</key><string>0.1.0</string>
 <key>CFBundleVersion</key><string>0.1.0</string>
 <key>LSMinimumSystemVersion</key><string>12.0</string>
 <key>NSHighResolutionCapable</key><true/>
 <key>NSPrincipalClass</key><string>NSApplication</string>
</dict></plist>
PLIST
```

`CFBundleExecutable` must equal the filename in `MacOS/`, and `CFBundleIconFile` the basename
of the `.icns` in `Resources/` (no extension). For a **windowless** service add
`<key>LSBackgroundOnly</key><true/>`; for a **GUI app omit it**, or the window never appears.

## The icon

Each `.iconset` slot must be a PNG at its OWN pixel size — `cp`-ing one image across every
slot leaves a 1024px bitmap labelled `icon_16x16` and the small sizes render badly.

```bash
mkdir -p icons.iconset
for spec in "16 icon_16x16" "32 icon_16x16@2x" "32 icon_32x32" "64 icon_32x32@2x" \
            "128 icon_128x128" "256 icon_128x128@2x" "256 icon_256x256" \
            "512 icon_256x256@2x" "512 icon_512x512" "1024 icon_512x512@2x"; do
  set -- $spec
  sips -z "$1" "$1" master.png --out "icons.iconset/$2.png" >/dev/null
done
iconutil -c icns icons.iconset -o "$APP/Contents/Resources/appicon.icns"
```

Renaming `.png` → `.icns` renders a blank icon; the `iconset` + `iconutil` step is mandatory.

### Drawing the master PNG
- **Author at 1024 and design ONE bold shape.** A Finder/Dock icon is read at 16px, so fine
detail becomes mush. High-contrast silhouette beats clever detail.
- **Supersample the glyph (author at 2-4x, then `cv2.resize` with `INTER_AREA`) and composite
  the glyph through a mask** rather than overdrawing it. Overdrawing leaves stair-stepped
  rounded corners at the large sizes where the icon is actually seen.
- Build the rounded square with `_rounded_rect_mask`-style mask, apply it to the tile's alpha,
  then blend the glyph mask over the tile RGB. Keep the PNG as a real RGBA image.

## Pitfalls

- **Do NOT `exec` the interpreter from the launcher — run it as a child and `wait`.** With
  `exec`, the process image becomes the framework interpreter and macOS gives the Dock the
  *interpreter's* icon (e.g. Python's rocket), not your bundle's. Staying alive as the parent
  keeps the bundle identity, so the Dock shows the custom icon. Plain `"$VENV_PY" -m app`
  followed by `exit $?` is the correct shape.
- **Re-register with Launch Services after building, or Finder may keep showing the old or
  generic icon** (it caches):
  `/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP"`
  and `touch "$APP"`.
- **A Finder launch has no terminal, so errors vanish.** Redirect output to a file
  (`~/Library/Logs/<app>.log`, timestamped per launch) and raise a dialog on failure:
  `osascript -e 'display alert "<App>" message "..."'`. Same for a missing venv/repo — alert,
  don't exit silently.
- **Never hardcode `CFBundleShortVersionString` in the build script.** Derive it from the app's
  own `__version__` so the plist cannot drift from the code it contains (strip the descriptive
  suffix — macOS wants dotted numeric). A bundle whose plist disagrees with its own source is
  worse than one with no version, because it is confidently wrong. Check with
  `plutil -p "$APP/Contents/Info.plist" | grep -E 'ShortVersion|CFBundleVersion'` after each build.
- Pair with the interpreter's bundle resource: place the 1024px master PNG in `Contents/Resources/`
  too and set it as the window icon at runtime, so the running window is branded even on the
  non-bundled launch path.
- Gatekeeper: a locally built bundle carries no quarantine attribute and launches normally.
  A bundle that was downloaded/zipped needs right-click → Open once.
- `open -a "$APP"` starts it; killing the launcher's parent does not always kill the child —
  `pkill -f "<module path>"` targets the app itself.

## Verify (do not assume the icon attached)

```bash
plutil -lint "$APP/Contents/Info.plist"                       # plist is valid
plutil -p "$APP/Contents/Info.plist" | grep CFBundleIconFile  # points at the icon's basename
find "$APP" -type f                                          # MacOS/launcher, Resources/*.icns, Info.plist
iconutil -c iconset "$APP/Contents/Resources/appicon.icns" -o /tmp/icns_check.iconset
ls /tmp/icns_check.iconset                                    # expect all 10 sizes back
md5 -q "$APP/Contents/Resources/appicon.icns" <source>.icns  # bundled == generated
pgrep -fl "MacOS/launcher"                                    # launcher alive as the PARENT
pgrep -f "<module path>"                                      # the app itself is running
tail ~/Library/Logs/<app>.log
```

The `iconutil` round-trip is the load-bearing check: if the `.icns` is malformed or the plist
points at the wrong basename, Finder silently falls back to the generic icon and nothing errors.

## See also
- SKILL.md body — the `.command` pitfalls (PYTHONPATH/PATH exports, pkill spacing) all still
  apply to the launcher inside the bundle.
- `cloudflared-tunnel-demo` — pair a `.app` with a wss tunnel for live https demos.
