# Hiding dev/test-only UI + professional terminology (MARU)

## When this applies
The user treats MARU as a product that must read like an expensive, professional
tool (ArcGIS / Google Earth grade). Two recurring asks:

1. **Hide personal/dev/test rigs from the shipped surface** but keep them usable
   for the owner's own demos — without spelling them out in the how-to.
2. **Rename amateur-sounding terms** to professional ones (e.g. "Wall" →
   "Digital Twin Overlay") across every button, label, doc, and the Obsidian how-to.

Both came up in the same session and were solved with the patterns below.

---

## Pattern A — Hidden admin unlock (keep a feature usable but invisible)

Use when a feature (e.g. the S22 / iPhone edge node) is a personal test artifact
that must NOT appear for normal users, yet the owner needs to flip it on for demos.

### The mechanism (proven, lives in `src/useEdgeUnlock.js`)
- A `localStorage` flag (`maru_edge_unlocked`) is the single source of truth.
- A `useSyncExternalStore` hook (`useIsEdgeUnlocked`) so every mounted component
  re-renders the instant the flag flips — no manual prop drilling.
- A hidden gesture listener (`useEdgeUnlockListener`): press the same key **three
  times within ~1.2 s** (e.g. `E E E`). No button, no label, not in the how-to.
- Undiscoverable by design: it is intentionally absent from Settings, the how-to,
  and the InfoModal.

### Gate every surface the feature touches
For the S22 edge node the gates were:
- Settings menu item — filter `SETTING_ITEMS` to drop the `edge` entry unless unlocked.
- Settings detail panel — `{view === 'edge' && edgeUnlocked && (...)}`.
- Bottom-left connection pill (`ConnectionLaunch`) — `if (!useIsEdgeUnlocked()) return null`.
- The console branch + on-map entity (`AssetEntities`) — `showS22 = mode === 'android' && geo && edgeUnlocked`.
- Purge device names from **all** user-visible copy (Settings blurbs, InfoModal
  "Getting Started", the in-app How-To, the Obsidian how-to). Say only
  "Edge Connection" / "live edge feed".

**Keep the backend untouched** (`apiUtils`, Vite proxy router, `EdgeDataContext`,
`ConnectionSettings` internals). Only *visibility* is gated, so the rig still
works the moment the flag is set.

---

## Pattern B — Terminology rename (keep internal identifiers, change only visible text)

Rule that avoids breakage: **rename user-facing strings, leave code identifiers
alone.** Internal names like `twinWalls`, `showTwinWall`, `editingWallId`,
`TwinWallStudio`, and the Cesium entity ID `twin-wall-${id}` are plumbing — they
never render to the user. Renaming them ripples through context wiring for zero
user benefit and risks regressions.

### "Wall" → "Digital Twin Overlay" (the rename actually shipped)
Visible strings changed (internal ones left intact):
- Map Control group header: `Digital Twin Overlay`
- Toggle: `Show overlay on map` (was "Show wall on map")
- Badge noun: `overlay` / `overlays`
- Studio lead + label: `Station ID` (was "Wall ID"), `SAVE OVERLAY`
- HUD/error banners: `OVERLAY`, `Loading overlay assets…`
- In-app How-To + Obsidian `Settings/How to use MARU.md` §4: every "Wall" →
  "Overlay" / "Digital Twin Overlay" / "Station ID".

Search order that worked: `grep -ri "wall"` across `src/` and the vault, then
split matches into "visible text" (rename) vs "identifier / comment / CSS class /
entity id" (leave). Confirm with a second grep after editing that no *visible*
"wall" remains (remaining hits should all be `twinWall`, `TwinWall`, `editingWallId`,
`twin-wall-` id, or comments).

### Picking the term
- Prefer GIS-native vocabulary the user already uses elsewhere (MARU already had
  "Data Overlays", so "Digital Twin Overlay" sat in the same family).
- When unsure, offer 2–3 options and let the user pick rather than guessing the
  final wording.

---

## Build-trap lesson (this session)
`npm run lint` + `npm run build` green does **NOT** guarantee the page runs.
A ReferenceError from an undefined closure variable (e.g. `AssetEntities` reading
`edgeUnlocked`, which was only defined in the parent `DashboardInner`) escapes
Vite's build entirely and only throws at page load.

**Rule:** any variable a component reads must be defined *in that component* (or
passed as a prop), not assumed from a sibling/parent scope. When you add a flag
consumed by several components, call the hook (`useIsEdgeUnlocked()`) at each
call-site — do not rely on a variable declared in one component being visible to
another. Re-run the dev server and click through the gated path after any flag
addition.

---

## How-to / Obsidian exclusion rule
When a feature is hidden behind admin unlock, it must also be **absent from every
onboarding doc** (in-app How-To flyout + `Settings/How to use MARU.md`). The
shipped narrative should describe only the professional, always-available surface.
The vault dev notes (HermesProgress, client-layer scheme) are internal and may
keep historical "the Wall" wording, but user-facing docs must not.
