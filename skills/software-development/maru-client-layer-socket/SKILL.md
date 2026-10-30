---
name: maru-client-layer-socket
description: Build client-self-service layers in MARU (my-digital-twin) using the "tolerant socket" pattern — one generic card schema that clients fill via their own AI + a QR-distributed spec, rendered by a single generic component. Use when the user wants clients to bring their own asset/operation data/layers without per-client code, or mentions "client layer", "own layers", "socket match", "QR spec", "AI reads client input".
---

# MARU Client Layer — Tolerant Socket

## When to use
- User wants clients to bring THEIR OWN data/layers into MARU (asset- or operation-focused).
- User mentions "client layer", "own layers", "socket match", "QR spec", "AI reads client input", "broad tolerant scheme".
- User accidentally removed a provider/layer during broken-link cleanup and asks to restore one source while keeping others (e.g. weather + AIS split; keep weather, drop vessels).

## Core model (the 8-year-old version)
MARU is a DUMB TERMINAL that accepts ONE card shape. The QR hands the client the
*spec* (the schema). The client's OWN AI translates their messy feed into a card.
MARU validates 3 required fields, leniently accepts the rest, renders points.
NO AI in MARU's live path. NO per-client code.

## The schema (all-optional EXCEPT the anchor)
Required (strict — validation gate fails without these):
- `layer.layer_id`  (tenant + layer namespace)
- `layer.owner_key` (security boundary / tenant scoping)
- `entity.id`       (unique within layer)
- ONE `anchor`: `{type:"geo", lat, lon}` OR `{type:"building", building_id, floor?, zone?}`
  OR `{type:"twin_slot", building_id, slot}` (NET-NEW — see Receiving End below; the
  SHM-grade anchor that pins data ON a structure component, e.g. a front-door sensor)

Optional input types (matches the user's stated needs):
- `readings[]`  — sensor time-series {param, value, unit, ts} → popup table / sparkline
- `media[]`     — image[] defect/incident {type:"image", kind, url, caption, ts} → carousel
- `documents[]` — certs JSMS/Permit {type:"certificate", kind, url, expiry, ref} → badge + expiry warn
- `properties{}`— free-form client KV
- `status` / `severity` (0–3) / `group` / `tags[]` / `label`

## Build order (forced — don't over-build)
1. schema (design artifact) — DONE: `DT/MARU Client Layer Scheme — Tolerant Socket.md` in obsidian_maru_1
2. generic renderer — ONE component consumes any valid card
3. validation gate — strict-3, lenient-rest; return `"missing: lat"`, never silent garbage
4. shareable spec page + QR (distribution hook)
5. per-client tenant scoping via `owner_key` (extends governance egress registry)
6. (later) AI translator — start as you-with-a-prompt, automate after 1–5 land

## Receiving end — what MARU prepares to RECEIVE the socket
The socket (card schema) is the wall outlet; MARU must MOUNT it. Two pieces:
1. **Generic layer shell** ("junction box"): one empty `layer_id`+`owner_key` + Map
   Control toggle + `<ClientLayerRenderer>` mount + a card-ingest UI. "N sockets
   enabled" = pre-seeded (greyed) placeholder anchors the integrator lays out
   where data is expected. This is the NEXT code chunk (wiring already known).
2. **3D digital twin of the station** ("the wall"): NET-NEW. Current `building`
   anchor has NO 3D model behind it (falls back to a coordinate). Needs a
   **twin registry** = `building_id` → `.glb` model + world transform + named
   sub-anchors (`front_door`, `pump_room`, `floor3_zoneB`) with local positions.
   Integrator places the model + names slots; client tags data to SLOT NAMES
   (no coordinates). The `twin_slot` anchor resolves to a point ON the structure.
   This is the SHM-grade answer (sensor tied to structural element, not 40 m off
   at the building's lat/lon). See `references/receiving-end.md` for the diagram,
   anchor-type table, integrator/client division, and build addendum (A→B→C→D).

## Build addendum (extends the forced order above)
- (0) socket schema + generic renderer — DONE (design note + `clientLayerSchema.js` + `ClientLayerRenderer.jsx`)
- (A) wire socket into live map (layer shell + context flag + panel row + ingest UI) — NEXT code chunk
- (B) **twin registry + 3D model placement tool (integrator)** — BUILT 2026-07-19 (see "The Wall" below). Files: `src/twin/twinRegistry.js`, `src/components/DigitalTwinWall.jsx`, `src/components/TwinWallStudio.jsx`.
- (C) `twin_slot` anchor type + sub-anchor resolve in `resolveAnchor`/renderer — SCAFFOLDED: `resolveAnchor` accepts `wallResolver`; live data pinning onto slot markers not yet rendered (next chunk).
- (D) tenant scoping via `owner_key` (already in schema; wired in step A)

## The Wall — 3D receiving end (BUILT 2026-07-19)
The "wall" = a per-station 3D surface in MARU where the integrator drops the
client's model + optional Lidar, places it at the station, and NAMES SLOTS that
socket data pins onto. This is the SHM-grade move: data ON a structural element,
not a vague lat/lon.

**Format decision (durable):** SketchUp `.skp` MUST be exported to **glTF / GLB**
before upload — Cesium loads it natively (gzip-friendly, Draco-compressible).
Lidar = Cesium 3D Tiles (`.3dtiles`). MARU does NOT translate .skp itself.

**Files (all new, typed, KISS/DRY):**
- `src/twin/twinRegistry.js` — `upsertTwinWall/removeTwinWall/validateWall/
  resolveTwinSlot/twinWallCount` + `initTwinState()`. NO cesium import (lives in
  `EdgeDataContext` so map + panel share ONE source of truth).
- `src/components/DigitalTwinWall.jsx` — renders model (`resium <Model>`,
  east-north-up transform), optional Lidar (`<Cesium3DTileset>`), NAMED SLOT pins
  (`<PointGraphics>` + label). Click → slot detail. Self-gates on `showTwinWall`.
- `src/components/TwinWallStudio.jsx` — right flyout to author a wall (model URL,
  format, Lidar URL, station lat/lon, named slots).
- Wired like EVERY MARU layer: Map Control "Digital Twin Wall" group (toggle +
  Open Studio), `showTwinWall` context flag, mounted in `<Viewer>`, single-active
  flyout slot.

**Loop-closer (scaffold only):** `clientLayerSchema.resolveAnchor` accepts
`wallResolver` so a card with `{building, slot}` resolves to the SLOT marker
position. Live rendering of client cards onto slot pins is the next chunk (the
"wow" — a front-door reading ON the front-door pin).

Full technique + resium pitfalls in `references/the-wall-build.md`.

## Implementation notes (matches MARU stack)
- Box 1 = Vite + React SPA (NEVER Next.js/monorepo). Map = Cesium (resium).
- A client layer is CLIENT-FED, not egress-fed → NO egress driver. It reads a
  pasted/uploaded card (or fetches from a client URL behind a Vite proxy if needed).
- Generic renderer maps card → resium `<Entity>` with position from `anchor`;
  popup renders `readings`/`media`/`documents`/`properties` by type.
- `validateCard(card)` is a PURE function → {ok, layer, entities[], rejected[], error}.
  Render only placeable entities; surface a layer-level warning for rejected ones.
- Building-anchored: if `anchor.type==="building"`, attach to the digital-twin
  structure if it exists, else drop at the building's registered coordinate.
- `twin_slot` anchor: resolve via the twin registry to a local offset ON the model;
  if the model/registry is absent, fall back to the building's coordinate (never crash).

## Pitfalls
- Don't put AI in the render path (perf + drift). AI only at onboarding / on schema drift.
- Don't hand-write per-client code. The whole point is ONE schema + ONE renderer.
- When restoring a weather/data layer after broken-link cleanup: provider rows must be restored consistently across `layerRegistry.js`, `MapControlPanel.jsx`, and explanatory code comments; restoring the registry alone leaves the UI dead/wrong.
- "Lookup from Obsidian + GitHub only" rule: when a user says a removed endpoint must come exclusively from local vault/Git history, do NOT invent endpoints. Exhaust `git log -S/-p` and local markdown first; if absent, scaffold a placeholder row with the URL marked as dotted-line rather than guessing a real endpoint.
- Schema drift: card carries `schema_version`; on mismatch, flag layer + offer re-map,
  degrade gracefully like other layers.
- Tenant scoping: a card's entities MUST be namespaced by `owner_key`+`layer_id`
  so Client A can't land on Client B.
- Keep chunks small (standing UI/UX rule); self-recheck overlap before claiming done.
- EXPLAIN VISUALLY for this user: when describing abstract architecture (the socket,
  the receiving end, data flow), prose alone did NOT land — user said "draw it for me".
  Lead with an ASCII/mermaid diagram + the 8-year-old metaphor (wall outlet / junction
  box / wall), THEN the detail. Matches standing user preference for plain-language
  and analogy before jargon.
- Recovery from lint/build breakage: when `npm run build` or `npm run lint` fails on a
  Panel/Context mount wiring path in `App.jsx`, DO NOT hand-patch control-panel UI rows
  from partial file reads. That is how bad regressions happen. Instead:
  1) revert the panel file to the last committed state with `git checkout -- <panel path>`
  2) re-apply the panel patches in small targeted steps with a verification read after
     each edit before moving on. The regression recovery is a separate action, not
     something to undo with a full-file rewrite in the same turn as the next patch.

## References
- `references/receiving-end.md` — socket → twin receiving-end diagram, anchor-type table, integrator/client division, build addendum (A→B→C→D).
- `references/the-wall-build.md` — concrete build recipe for "the Wall": glTF/GLB format rule, resium `<Model>`/`<Cesium3DTileset>` prop facts, ESM import pitfall, upright transform, slot-click handling, state placement, and the 7-touch "wire a new MARU layer" template.
