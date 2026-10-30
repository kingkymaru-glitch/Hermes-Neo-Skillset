---
name: local-webapp-verify
description: "Verify a local web app actually serves your edits."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [web, flask, verification, debugging, dev-server, localhost]
    related_skills: [systematic-debugging, vite-build-verification, source-vs-rendered-verify]
---
# Local Web-App Verification (served, not built)

## When to use
You changed files in a web app that runs locally (Flask, FastAPI, Django dev
server, Node/Express, etc.) and need to confirm the change is actually visible
to the user — especially when the user says "I don't see any changes you made."

This is a Phase-1 verification step from `systematic-debugging`, specialized for
the recurring failure modes below.

## Iron Law
"Done" means the **running server's HTTP response** contains the change — not
that the file is written, not that a build exited 0. Prove it with a request.

## Pitfall 1 — dev-server template cache (most common cause of "no changes")
- **Symptom:** `read_file` shows the edit on disk, but the user's browser shows
  the old page.
- **Root cause:** Flask compiles templates to memory and does NOT auto-reload
  when `debug=False`. Jinja2 caches compiled templates; live-edited files never
  reach the browser until the process restarts.
- **Detect:** `curl -s http://localhost:PORT/ | grep -n 'unique-new-string-from-edit'`
  → if it returns nothing but the file has the string, the server is stale.
- **Fix (local dev only):**
  ```python
  app = Flask(__name__)
  app.jinja_env.auto_reload = True
  app.config["TEMPLATES_AUTO_RELOAD"] = True
  ```
  This makes future edits show without a manual restart. (Keep `debug=False` in
  prod; this flag alone is enough.)
- **Or:** restart the server process (kill PID holding the port, re-launch).
  Find it: `lsof -nP -iTCP:PORT -sTCP:LISTEN`.

## Pitfall 2 — file:// is blocked; http://127.0.0.1:PORT works (and is preferred)
- `browser_exec` refuses `file://` URLs outright: the tab lands on
  `chrome-error://chromewebdata/` and the page never loads, so every later
  `js()` call dies with "parameter 1 is not of type 'Element'". Do not debug
  the page — you never loaded it.
- **Fix:** serve the directory and navigate over HTTP. For a standalone HTML
  file (no build step, no framework) this is the whole setup:
  ```bash
  cd /path/to/dir && python3 -m http.server 8123 --bind 127.0.0.1 &
  ```
  then `new_tab("http://127.0.0.1:8123/<file>.html")` + `wait_for_load()`. Tear
  the server down when done (`pkill -f "http.server 8123"`) — the founder does
  not want lingering services on the Mac.
- A loopback/private-IP block has been reported historically, but on current runs
  `http://127.0.0.1:PORT` navigates fine. Only if it is genuinely blocked fall
  back to headless Chrome + `vision_analyze` (recipe below).
- **Therefore you CAN usually drive the local UI with browser_exec.** When it is
  not blocked, prefer it over headless screenshots: `js()` gives you
  `getComputedStyle`, which proves a restyle far better than pixels can (see
  Pitfall 6).
- **Headless render recipe (Chrome on macOS at
  /Applications/Google Chrome.app):**
  ```bash
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless=new --no-sandbox --use-gl=angle --use-angle=swiftshader \
    --disable-dev-shm-usage --window-size=900,700 \
    --screenshot=/tmp/app.png --virtual-time-budget=7000 \
    "http://localhost:PORT/path?query=..." 2>/dev/null
  ```
  - `--use-angle=swiftshader` is *meant* to give software WebGL so three.js /
    canvas sites render without a GPU. **But on this Mac's headless Chrome it is
    UNRELIABLE: it can fail to create a GL context and throw
    `Uncaught TypeError: Cannot read properties of null (reading 'width')` at
    `WebGLRenderer` init — producing a BLANK screenshot even though the exact same
    code renders fine in a real browser.** Treat a blank headless shot of a
    three.js scene as a *possible false negative*, NOT proof the app is broken.
    See Pitfall 5 for the diagnostic + fallback.
  - Then call `vision_analyze(image_url="/tmp/app.png", question="...")` to read
    the actual pixels — confirm the 3D scene, pins, labels, and absence of errors.
- **Combine with curl/grep** for non-visual proof:
  - `curl -s http://localhost:PORT/path | grep -n 'unique-marker'` → change served.
  - `curl -s -X POST .../api/route ...` to exercise backend routes.
  - A Python `requests` script that mimics the browser `fetch` to prove save/load.
- **Verification-target correction:** when the user says "verify on localhost,"
  the target is the Mac's own browser via `localhost` — NOT a phone/remote
  device. Do not reach for a mobile device unless the user names one. (Seen:
  agent offered a LAN/phone URL when the user explicitly wanted localhost only.)
- **State honestly:** report what the screenshot actually shows. If headless
  WebGL failed to paint (blank three.js scene), say so explicitly and do NOT
  claim a visual check — fall back to the Pitfall 5 Node data-wiring proof and
  ask the user to eyeball the real browser. Only claim a verified visual when
  pixels are genuinely present.
- See `references/headless-render-verify.md` for the full recipe + a three.js
  pin-rendering pitfall (sprite CanvasTexture fails under swiftshader; use a
  solid mesh pin instead).

## Pitfall 3 — orphaned handlers when removing legacy markup
- Moving a feature to a new page often tempts you to delete the old markup.
- **Before deleting**, grep for every `getElementById(...)` / `.onclick` that
  referenced the IDs you'd remove. If any run at *load time* (not only inside
  guarded callbacks), they throw on `null` and **halt the entire script** —
  breaking the page you were told NOT to touch.
- **Safer:** keep the orphaned element in the DOM (hidden via `display:none`),
  so existing handler wiring stays valid, and only repoint the trigger (e.g.
  button → `window.location.href = '/newpath'`). Clean up dead handlers only in
  a later, deliberate pass.

## Pitfall 4 — inline `<script>` syntax break survives curl, breaks at runtime
- Verifying the *served HTML* (curl + grep) proves the edit reached the browser, but
  it does NOT catch a JavaScript syntax error inside an inline `<script>`. A broken
  script still shows the markup yet silently fails every handler — the user sees
  "nothing happens."
- **Before committing a UI edit**, extract the inline script and syntax-check it:
  ```bash
  python3 - <<'PY'
  import re
  html = open('templates/page.html').read()
  js = re.search(r'<script>(.*)</script>', html, re.S).group(1)
  open('/tmp/inline.js','w').write(js)
  PY
  node --check /tmp/inline.js && echo "JS SYNTAX OK"
  ```
- Combine with the curl/grep loop: grep proves the change is *served*; `node --check`
  proves the script still *parses*. Both are cheap and run pre-commit.

## Pitfall 5 — headless WebGL false-negative (blank 3D scene ≠ broken app)
- **Symptom:** headless Chrome screenshot of a three.js / WebGL app is totally
  blank (no canvas content) even though identical code rendered fine in a prior
  headless run or in a real browser.
- **Root cause seen on this Mac:** swiftshader WebGL context creation fails under
  `--headless=new`. The console shows
  `Uncaught TypeError: Cannot read properties of null (reading 'width')` at the
  three.js `WebGLRenderer` constructor. This aborts the whole module before the
  render loop runs → blank. It is ENVIRONMENTAL, not a code bug.
- **Diagnose, don't guess:**
  1. Re-run the screenshot 3×. If all three are byte-identical blanks, it's
     deterministic in this headless config (not a fluke).
  2. Capture console: add `--enable-logging=stderr --v=1` and grep for
     `Uncaught TypeError` / `reading 'width'` / `WebGL`. A GL-context error there
     confirms the false negative.
- **Fallbacks that actually prove the app (no GPU needed):**
  - **Data-wiring proof (deterministic, no WebGL):** run the app's data logic in
    Node — fetch/parse the JSON the viewer loads, replicate the position math,
    assert counts. Proves the data path is correct even when pixels can't paint.
  - **Harden + re-test:** guard renderer creation in try/catch, set a sane
    fallback size (`innerWidth || 900`), and retry. If it *still* blanks in
    headless, stop trusting pixels here.
  - **Defer to the user's real browser:** state plainly — "headless WebGL on this
    Mac won't paint; open http://localhost:PORT/path in your browser and tell me
    if the scene shows." Do NOT claim the visual is verified from a blank shot.
- **Rule of thumb:** a blank headless 3D screenshot is a *verification-tool
  limitation*, not evidence of a defect. Prove the data layer in Node, harden the
  init, then ask the user to eyeball the real render.

## Pitfall 6 — verifying a CSS restyle without pixels
A palette/theme swap must be proven from **computed styles**, not from looking
at the page — you cannot read screenshots. Serve the file (Pitfall 2), then read
`getComputedStyle` for each selector that carries the theme in ONE `js()` call and
assert the returned values. Three traps:
- A cell styled with a **gradient** reports `backgroundColor: rgba(0,0,0,0)` with a
  non-empty `backgroundImage`. Read `backgroundImage`, or you will wrongly report
  the cell as unstyled.
- A `:root` custom property is usually reused in BOTH roles — a fill and a text
  color on a light surface. Changing only its VALUE follows both, so when the
  palette flips to a dark background those text colors go dark-on-dark and the UI
  becomes unreadable with no error. Grep every use of the variable and split
  fill-role from text-role; give text-role uses their own light value.
- **`getComputedStyle(el, '::-webkit-<pseudo>')` returns the ORIGINATING
  ELEMENT's box, not the pseudo-element's own style.** Seen on a range slider:
  `::-webkit-slider-runnable-track` (styled 4px) reported `height: 18px`,
  `::-webkit-slider-thumb` (styled 13×13) reported the full input width, and
  `backgroundColor` came back `rgba(0,0,0,0)`. Chrome does not resolve `-webkit-`
  pseudo-elements through the two-argument form. Do NOT conclude the rule failed
  and do not "fix" CSS that is working — verify with pixels instead: screenshot
  the control, or crop + upscale it, and read the rendered colour bands (a 6px
  non-background band across the row = the 4px track plus two 1px borders).
  `getComputedStyle` on the element ITSELF (`fontSize`, `padding`, `borderRadius`)
  is reliable; only the pseudo-element form lies.

Also assert the app still WORKS, not just that it is colored (row/stat/cell
counts). Full recipe, the leftover-hex sweep, the whole-`<style>`-block splice,
and the JS-inline-style trap: `references/theme-restyle-verify.md`.

## Pitfall 7 — a row of controls clipped by its container (verify by GEOMETRY)
- **Symptom:** "the buttons exceeded the tab width and are buried behind the tab
  border" / a tab strip, button row, or chip row loses its last item — cut off at
  the container's edge. Nothing errors; the rest of the page looks fine.
- **Root cause:** the children's total width exceeds the container's INNER width
  (`clientWidth` = width minus padding and borders, NOT `getBoundingClientRect().width`),
  and a `display:flex` row with no `flex-wrap` silently overflows instead of wrapping.
  Responsive caps (`sm:max-w-96` etc.) shrink the container at some widths while the
  children keep fixed padding, so the break appears only at those widths.
- **Fix:** shrink the CHILD with a scoped modifier class. The shared base class is
  usually app-wide and may carry a protected mobile tap target
  (e.g. `@media (max-width: 640px) { .mb-btn { min-height: 44px } }`), so shrinking
  IT is the bigger, riskier change — do that only when the user explicitly asks for
  app-wide. Read the compiled CSS to confirm the media query still wins on source
  order; a desktop padding reduction must not collapse the tap target. Add
  `flex-wrap: wrap` to the row as a guard so a future added item wraps rather than clips.
- **Prove it with geometry, not by looking.** Render the real compiled CSS plus the
  real markup in a browser, then in ONE `js()` call compare each child's
  `getBoundingClientRect().right` against the container's `.right`, count rows as
  `stripHeight / firstButtonHeight`, and check the failure modes the user will name
  even when nothing is actually clipped:
  ```js
  const d = document.getElementById('container'), s = d.querySelector('#strip');
  const dr = d.getBoundingClientRect(), sr = s.getBoundingClientRect();
  const rs = [...s.children].map(b => b.getBoundingClientRect());
  // rows    = Math.round(sr.height / rs[0].height)
  // clipped = rs.some(r => r.right > dr.right + 0.5)
  // wrapped = rs.some(r => r.height > Math.min(...rs.map(x => x.height)) * 1.6)
  // overlap = pairwise rect intersection among rs[]
  // air     = gaps between adjacent buttons, e.g. rs[1].left - rs[0].right
  ```
  Green = `clipped === false`, `rows === 1`, `wrapped === false`, `overlap` empty, AND
  the gap list identical to the pre-edit measurement. **The gap check is not
  optional:** a restyle that shrinks children while leaving container gaps alone can
  still be reported as "extended gaps between buttons" — compare the numbers, do not
  eyeball them. Report the actual numbers.
- **Set the viewport BEFORE navigating, and re-navigate after every change.** A
  device-metrics override applied to an already-loaded page does not reflow it — the
  measurement silently returns the OLD width's geometry (seen: `window.innerWidth`
  still reporting the desktop value while emulating a phone). Sequence per width:
  `cdp('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=D,
  mobile=M)` → `goto_url(...)` → `wait_for_load()` → measure. Never reuse one
  navigation across widths.
- **Fixture recipe (no build, no framework needed):** copy the app's real built CSS
  out of its bundle dir (e.g. `.next/static/chunks/*.css`) into a FLAT fixture
  directory next to a hand-written HTML file that reproduces the container and its
  children with the exact same class names, serve that directory, and measure.
  Copying beats referencing the deep bundle path — and **curl the CSS asset first**
  (`curl -s -o /dev/null -w '%{http_code}' …/real.css` → must be 200) before trusting
  any measurement: a 404 on the asset leaves every class silently unstyled and makes
  the geometry numbers meaningless.
- **Why not just screenshot it:** `vision_analyze` on a clipped strip reads as "text is
  missing" but cannot say by how many pixels, and cannot distinguish "clipped by the
  container" from "wrapped to a second row". Geometry gives you both.

## Standard verification recipe
1. Make the edit.
2. If the server was started before the edit, restart it OR rely on
   `TEMPLATES_AUTO_RELOAD` (set it if not already).
   **Confirm the server actually bound the port** — `next start -p PORT` (and most dev
   servers) fails silently when the port is already held by another app, and a stale
   server from an earlier session keeps answering on that port. Check
   `lsof -nP -iTCP:PORT -sTCP:LISTEN` for the expected process AND
   `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:PORT/<known-route>`
   before believing any measurement. On this Mac port 3000 is another app's frontend;
   give the app under test its own port (e.g. 3210).
3. `curl -s http://localhost:PORT/ | grep -n '<your-unique-marker>'` → must print.
4. For each new/changed API route: `curl` it (GET list, POST create, DELETE…)
   and assert the JSON shape.
5. For frontend save flows you can't click: replicate the `fetch` with `requests`
   (same payload) and confirm the backend round-trip.
6. Report exactly what was proven vs. what needs the user's eyes.

## Tight feedback loop (from systematic-debugging)
The grep against the live server IS the red/green loop: red = old/stale,
green = edit served. Run it after every UI change, not just at the end.
