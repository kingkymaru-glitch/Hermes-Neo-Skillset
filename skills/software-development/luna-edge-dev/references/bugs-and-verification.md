# Luna-EDGE — bugs fixed & verification recipes (session detail)

## Bug 1 — video frame squashed / detection boxes misaligned
- Root cause: `paint()` did `ctx.drawImage(latestBitmap,0,0,canvas.width,canvas.height)`,
  stretching a 16:9 frame into a tall canvas. Also broke Learning-mode labels (drawn on
  warped coords -> wrong training boxes).
- Fix: contain maths in `paint()`:
  `scale=Math.min(cw/fw,ch/fh); dw=fw*scale; dh=fh*scale; dx=(cw-dw)/2; dy=(ch-dh)/2;`
  store `containRect={x:dx,y:dy,w:dw,h:dh}`; draw boxes via `bx=dx+x*sx`.
  `normBox()` maps the drawn canvas-px box into `containRect` then normalizes.

## Bug 2 — minimize worked, but NO way to expand again
- First attempt: CSS `#sidebar.collapsed ~ #launcher { display:inline-flex }`. FAILED
  silently — `#launcher` (outside `.row`) and `#sidebar` (inside `.row`) are NOT siblings,
  so the general-sibling selector never matched.
- Fix: drive visibility in JS inside `setCollapsed(v)`:
  `sidebarEl.classList.toggle('collapsed',v); launcherEl.style.display = v?'inline-flex':'none';`
  Removed the broken CSS sibling rule.

## Bug 3 — expand "button still missing" after Bug 2 fix
- Root cause: launcher was `position:absolute; top:16px; z-index:16`. The app bar is
  `position:relative; z-index:30; height:56px` and full-width, so the pill rendered
  BEHIND the header — present in DOM but invisible + unclickable.
- Fix: `position:fixed; top:72px; z-index:40` (sits just below the 56px bar, above it in
  stacking). Now clickable.

## Verification recipe (ad-hoc, no suite)
Throwaway script at `/private/var/folders/s5/zrb2gthn0qxbgr3c132r84m40000gn/T/hermes-verify-*.py`,
run, then `rm`. Always restart server first:
`pkill -9 -f "luna-edge/app.py"; cd ~/luna-edge && bash launch.command >/tmp/le.log 2>&1 & sleep 6`.
- Served-page assertions: `urllib.request.urlopen("http://127.0.0.1:8000/")`; regex count
  `{` vs `}` in `<style>` (balance); count `<div` vs `</div>`; inline JS -> `node --check`.
- Toggle sim: fake-DOM stub with `classList.toggle(c,v)` + `style` dict; call `setCollapsed`.
- Train proof (real): synthesize labeled frames -> `POST /api/learn/capture` (assert
  `saved>=10`) -> `POST /api/learn/train` (assert `os.path.exists(skills/<ds>.pt)`).
  ultralytics trains on MPS; 1-2 epochs take seconds.
- Flask test client alt: `app.app.testing=True; c=app.app.test_client()`.
Note: every `index.html`/`app.py` edit requires re-verifying against the LIVE server —
evidence from a pre-edit server is stale.
