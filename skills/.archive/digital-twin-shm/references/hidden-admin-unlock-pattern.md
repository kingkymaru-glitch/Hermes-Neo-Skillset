# Hidden admin-unlock pattern — keep MARU's shipped surface professional

## Trigger
When the user says a feature is "just for me to test / demo," "don't spell it out in
the how-to," or "keep MARU professional." This is a recurring MARU product-governance
rule: personal/test rigs (e.g. the S22 Ultra / iPhone edge node) must be hidden from the
normal UI and excluded from docs, but still reachable for the owner's own demos.

## What to build
A hidden, undiscoverable admin unlock that reveals the gated UI only when triggered,
and persists so it stays on for the demo session.

Pattern used for the S22/iPhone edge node (Verified: lint 0 errors, build green):
- `useEdgeUnlock.js` exports:
  - `isEdgeUnlocked()` — reads `localStorage['maru_edge_unlocked'] === '1'`.
  - `useIsEdgeUnlocked()` — `useSyncExternalStore(subscribe, isEdgeUnlocked, () => false)`
    so every mounted component re-renders on unlock.
  - `useEdgeUnlockListener()` — window keydown listener: presses `E` three times within
    1.2s → `unlockEdge()` (writes localStorage + notifies subscribers). Ignored while
    typing in an input/textarea.
- Wire `useEdgeUnlockListener()` once in `DashboardInner` (top-level).
- Gate every S22/iPhone surface behind `edgeUnlocked`:
  - Settings menu item: `SETTING_ITEMS.filter(item => item.key !== 'edge' || edgeUnlocked)`
  - Detail panel: `{view === 'edge' && edgeUnlocked && (...)}`
  - Bottom-left pill (`ConnectionLaunch`): `if (!useIsEdgeUnlocked()) return null`
  - S22 console branch: `{isS22Selected && edgeUnlocked ? (<S22Console/>) : (...)}`
  - On-map entity: `const showS22 = mode === 'android' && geo && edgeUnlocked`

## Keep the public surface clean
- Rename device-specific labels: `Edge Setting` → `Edge Connection`; blurbs
  `S22 / iPhone feed` → `live edge feed`.
- Purge device names from the how-to (in-app Settings ▸ How To AND Obsidian
  `Settings/How to use MARU.md`) and from InfoModal "Getting Started".
- Leave backend internals (`apiUtils`, `EdgeDataContext`, `ConnectionSettings`, proxy
  routing) UNTOUCHED — they keep working the moment the flag flips on.

## Gotcha (links to vite-build-verification Pitfall 6b)
When you add `edgeUnlocked` in a parent component, every nested component that READS it
must call `useIsEdgeUnlocked()` itself (or take it as a prop). A parent `const` is NOT
visible inside a nested function component — that slips through `lint`+`build` green and
crashes at runtime. `AssetEntities` needed its own `const edgeUnlocked = useIsEdgeUnlocked()`.

## How the user unlocks (for your own testing, not to be documented for them)
On a fresh browser, press `E` three times quickly → reopen Settings → "Edge Connection"
appears; the edge feed + S22 console work normally. Clearing `localStorage` re-locks it.
