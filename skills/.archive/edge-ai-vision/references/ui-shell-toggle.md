# UI shell: LunaV glass + minimize-to-pill (and the sibling-selector trap)

Reference impl for the Luna-EDGE control-panel shell. Reusable lessons.

## 1. Minimize toggle MUST be JS-driven, not a CSS sibling selector

**Bug (hit in prod):** floating control panel `#sidebar` with `position:absolute` over
the video; a `#launcher` pill should appear when minimized to bring it back. CSS used:

```css
#sidebar.collapsed { transform: translateX(-120%); opacity:0; pointer-events:none; }
#sidebar.collapsed ~ #launcher { display: inline-flex; }
```

This never fired: `#launcher` was placed as a sibling of `<header>`, while `#sidebar`
lives INSIDE `.row` — they are NOT siblings, so `~` never matches. Result: clicking
minimize slid the panel away with NO control to restore it. Silent, looks like a dead
button.

**Fix:** drive the launcher's visibility explicitly in JS. Never depend on a sibling
combinator for a show/hide the user must be able to reverse.

```js
const sidebarEl = document.getElementById('sidebar');
const launcherEl = document.getElementById('launcher');
function setCollapsed(v){
  sidebarEl.classList.toggle('collapsed', v);
  launcherEl.style.display = v ? 'inline-flex' : 'none';  // JS-driven, robust
}
document.getElementById('minBtn').onclick = () => setCollapsed(true);   // '–' in panel head
launcherEl.onclick = () => setCollapsed(false);                        // top-left pill
```

Rule of thumb: any toggle whose OFF state must be reversible by the user needs an
explicit visible affordance IN that off state. If hiding the panel also hides the only
button that reopens it, you've strung yourself. The collapsed state must show its own
"open me" control (here: a glowing top-left `L · Controls` pill).

## 2. Professional LunaV glass shell (design tokens)

Mirror LunaV Studio globals.css so the offline tool looks like a first-party product:

- `:root` tokens: `--lv-void:#14171c; --lv-panel:#1b1f26; --lv-inset:#0f1216;
  --lv-hairline:rgba(150,175,205,0.14); --lv-turq:#2f9bff; --lv-ice:#7db4ff;
  --lv-amber:#ffb340; --lv-red:#ff4d4d; --lv-green:#00c878; --lv-txt1:#e8eef4;
  --lv-txt2:#8fa1b3; --lv-glow:0 0 18px rgba(47,155,255,0.35);`
- Glass panels: `background: rgba(27,31,38,0.82); backdrop-filter: blur(22px);` +
  `border:1px solid var(--lv-hairline); border-radius:14px; box-shadow:0 10px 30px rgba(0,0,0,.45)`.
- Primary button: `linear-gradient(135deg,var(--lv-turq),#1b6fd0)` + `box-shadow:var(--lv-glow)`.
- Brand bar: `L` mark (gradient rounded square) + `LunaV EDGE` wordmark + uppercase subtitle.
- Live status pill: color-coded dot (idle/ws/live/stop) beats plain text.
- Grouped sections with dividers; ghost/teach/stop button variants; focus rings
  (`0 0 0 3px rgba(47,155,255,.18)`); custom `::-webkit-scrollbar`.
- Inter webfont (`fonts.googleapis.com`) with `-apple-system` fallback — degrades gracefully
  offline (field use). Do NOT add other CDN script tags (offline-first; see streaming-stability).
- Bottom railing: fixed `LunaV Labs` wordmark, glass, `border-top` hairline.
- Brand single line: `LunaV EDGE: OFFLINE DETECTION` (the `: OFFLINE DETECTION` muted grey,
  `EDGE` turquoise). L mark sized ~34px to match the single line height.

`object-fit:contain` math for the canvas (see aspect-ratio-ui.md) keeps native aspect ratio
so the video is undistorted AND training labels are correct.

## 3. JS-driven launcher is NECESSARY but NOT SUFFICIENT — it can still be hidden by the header

**Second bug (same feature, shipped after the sibling-selector fix):** even with
`setCollapsed()` setting `launcherEl.style.display='inline-flex'`, the expand pill stayed
invisible and unclickable. Cause: it was `position:absolute; top:16px` directly UNDER the
full-width 56px app bar, which sits at `z-index:30`. The pill rendered behind the header
and could never receive a click — indistinguishable from "missing button".

**Fix (both rules together):**

```css
#launcher { position: fixed; top: 72px; left: 16px; z-index: 40; display: none; /* ...glass pill */ }
```

- `position: fixed` (not absolute) so it anchors to the viewport, not the scroll container.
- `top: 72px` clears the 56px header with a 16px gap — sits BELOW the bar, fully visible.
- `z-index: 40` is ABOVE the header's `z-index:30` so it is clickable on top.
- Keep the JS `launcherEl.style.display = v ? 'inline-flex' : 'none'` from §1.

Checklist for any "collapsed control reappears as a floating button" pattern: it must be
(fixed OR absolute-with-correct-ancestor) AND have a z-index higher than any bar that
overlaps its `top` coordinate. A control that is logically shown but painted under another
layer is the same as a dead button.

## 4. Header page-mode switch (AI Learning <-> AI Detection)

For an app with two modes (live detection + in-app learning), put the mode toggle in the
header next to the brand, and make it a proper SWAP, not a flip-flop on one button:

- Place `AI Learning` button immediately after the brand block (top-left, before `.spacer`).
- Add a hidden `AI Detection` button (same slot). Drive both via one explicit function:

```js
function setLearning(on){
  learning = on;
  learnPanel.style.display = on ? 'block' : 'none';
  canvas.classList.toggle('learning', on);
  learnBtn.style.display = on ? 'none' : 'inline-flex';
  aiDetBtn.style.display  = on ? 'inline-flex' : 'none';
  if(on) refreshCls();
}
learnBtn.onclick = () => setLearning(true);
aiDetBtn.onclick = () => setLearning(false);
```

Why: a user entering learning mode needs an obvious "back to detection" control. Hiding the
AI Learning button and showing AI Detection in its place is discoverable; burying the exit
behind a panel-only toggle is not. The learning panel itself stays in the floating sidebar.
