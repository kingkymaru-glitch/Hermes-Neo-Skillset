---
name: lunav-studio
description: "LunaV Studio — 3D spatial risk inspection SaaS (Next.js + Three.js + Supabase + R2). Architecture, marker/model attachment, and modification patterns."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# LunaV Studio

LunaV Studio is a 3D spatial risk intelligence SaaS at `lunavsolution.vercel.app`. This skill covers the codebase architecture, how markers attach to 3D models, and patterns for extending the viewer.

## PRODUCT DIRECTION — custodian of the owner's maintenance record (founder, 2026-09)
The founder repositioned LunaV Studio: it is NOT a per-inspection project tool, it is a
**maintenance data management system and custodian of the asset owner's maintenance record**.
Inspector A enters data this year, Inspector B next year — both write into the SAME record
that belongs to the client. Three roles define the product:

    Owner (client)          — owns the asset AND the maintenance record. Lifetime.
    Custodian (LunaV)       — holds the record, makes it persist and be trustworthy.
    Contributor (inspector) — enters data, time-bound access, comes and goes.

Founder decisions already made (locked):
- **The client must be a REGISTERED user**, appointed by the inspector — the inspector
generates a registration/invite link; the client self-registers and becomes the data owner.
This creates a hard identity boundary between inspector and client. It replaces the
anonymous `client_share_token` gate as the acceptance path — an anonymous link cannot
answer "who accepted this".
- **Consortium chain: the client AND the inspector each run a validator node**, alongside
LunaV — a permissioned multi-party Besu network, not a LunaV-only chain.
- **Acceptance carries NO legal weight — it is purely a tamper-evidence layer.** The legal
instrument stays on paper: the printed report is signed by the professional engineer and
accepted by the client. The chain proves the digital record was not altered; it does not
replace the signature. This simplifies the build a lot (no compliant e-signature machinery
needed — a simple signed attestation suffices) and it is the split the founder wants.
- **Accepted reports to be anchored on Hyperledger Besu** as a NON-TRANSFERABLE record.
See the blockchain section below for the honest engineering read.

### Acceptance design (agreed direction, not yet built)
- **Unit of acceptance = the SUBMISSION (one inspection event), not individual findings.**
Per-finding clicking doesn't scale (180 findings) and isn't what an owner does. Keep a
per-finding DISPUTE lever underneath: accept the submission, flag specific findings with a
reason. Two layers, not one.
- **Acceptance cannot attach to a live view or an anonymous link.** Requires (a) a FROZEN
version of the submission, and (b) authenticated owner identity. The accepted artifact is
bound by version ID + hash.
- **Immutability rule:** accepted version is locked. Later edits create v2 which is PENDING
re-verification. Never mutate an accepted version; corrections are amendments.
- **Never auto-accept.** Pending stays pending until the owner acts (nudge + visible
UNVERIFIED badge). A timed auto-accept hands liability back to the platform — wrong for a
liability-averse founder.
- **Liability split to keep in the narrative:** the inspector asserts the finding; the
owner certifies "this entered my maintenance record as the authoritative entry"; the
custodian owns the integrity of both. The owner is NOT certifying the defect exists.
- Acceptance event records: owner user id + name + role, SERVER-side timestamp, version ID
+ content hash, dispute list, and the act itself (checkbox + typed legal name; add
IP/user-agent).
- The genuinely valuable artifact is the **hash-linked per-asset ledger**: each accepted
report carries the previous report's hash for that same asset, so tampering with 2026
breaks the 2027 link — verifiable forever, across inspectors and years.

### The ASSET entity — asset-centric vs project-centric (the founder did NOT follow this; explain it plainly, with an example)
Today everything hangs off `projects`, and a project conflates TWO things: the SITE (the
physical thing) and the JOB (this year's inspection). Nothing in the schema says the
"Substation KL-07 — 2026" project and the "Substation KL-07 — 2027" project are the same
physical asset, so the 2026 record is orphaned from the 2027 record and the whole
cross-year custody story has no anchor. Lead with that concrete example — the abstract
version does not land.

Introduce an ASSET entity — a permanent row + permanent ID for the physical thing. Every
inspection, every year, every inspector attaches to it. Custody tree:

    Owner (client account)
      └── Assets (Substation KL-07, Transformer T-12, …)
            └── Inspections (2026, 2027, 2028 — one per event)
                  └── Findings (markers, photos, dimensions, readings)

Everything that exists today maps onto the bottom three layers; the top two are missing.

Why it gates everything else:
- The hash chain needs a STABLE identifier to link against — the link is "this report's
  previous report FOR THIS ASSET". No asset ID → no "previous report" → no chain.
- The owner owns the ASSET, not the project. A project ends; the asset doesn't. Ownership
  attached to a project evaporates when the project archives.
- Cross-year comparison ("is T-12 degrading since 2026?") needs the anchor.

Migration: adding the parent layer, not a rewrite — bind each existing project to an asset.
Sub-decision to settle BEFORE building (retrofitting means re-linking the chain): flat
assets, or HIERARCHY (site → component → sub-component, defects attachable at any level)?

### Hyperledger Besu anchoring — honest engineering read (do not overclaim to the founder)
- A chain buys exactly three things here: tamper-evidence, independent timestamping, and
cross-party trust. It does NOT store the report (content stays off-chain), does NOT make
the data true, and does NOT by itself give legal signature validity (Malaysia: Digital
Signature Act 1997 / Electronic Commerce Act 2006 — the signature matters more than the chain).
- **The crux is WHO runs the validators.** Single-node Besu run by LunaV = a hash chain we
control → tamper-EVIDENT, not tamper-PROOF, i.e. roughly what an append-only Postgres
table already gives. Only a PERMISSIONED CONSORTIUM (LunaV + owner + optionally an
auditor/regulator each running a validator) makes "immutable" honest — and that is exactly
what Besu is for. Say this plainly; the founder wants facts over comfort.
- **CONFIRMED (founder): a consortium — the client and the inspector each run a node.**
Hold to these refinements when it is built:
  - **The validator is the ORGANIZATION, not the individual.** Inspectors rotate yearly;
    the node belongs to the inspection firm / the owner, keys held by the org — never
    hand a node to a person who will be gone next year.
  - **Running a node ≠ admin rights.** Validators only seal blocks; who may call
    `acceptReport` is contract logic. Do not conflate the two.
  - **3 nodes is thin.** IBFT/QBFT needs n = 3f+1, so 3 tolerates only 1 fault; 4 is the
    practical minimum. LunaV + owner + firm = 3 → consider a 4th neutral (auditor / PE firm).
  - **Small clients cannot run a node.** Enterprise owners (GLCs — they have IT infra) get a
    real validator; small clients get a READ-ONLY VERIFIER that checks the chain without
    sealing blocks. Node operation must never be a precondition for using the product.
  - Pitch symmetry worth using: the three product roles each run a node — contributor,
    owner, custodian sealing one ledger.
- **Because acceptance is NOT legal, hash the SCANNED SIGNED PAPER too** and store it
alongside the record hash: the chain then proves the digital record CORRESPONDS to the
PE-signed document. The paper carries the law; the chain carries the correspondence.
- **PDPA constraint:** no personal data on-chain (immutable ledger vs right-to-erasure).
Chain stores HASHES ONLY.
- **Not a transferable NFT.** Reports aren't transferable assets; transferability is
unwanted liability. Use a soulbound attestation (ERC-721 with transfers disabled /
ERC-5192, or an EAS-style attestation registry). Marketing may say "non-fungible report";
the contract must be non-transferable.
- On-chain tuple per acceptance: `assetId, reportId, reportHash, prevReportHash, ownerId
(hash/DID), timestamp, signature`.
- **SEQUENCING (the pushback that matters): build identity → freeze+hash → acceptance
event in Postgres FIRST, anchor to Besu LAST.** If the hash is computed from day one, the
chain is a plug-in, not a rewrite. Starting with Besu means months of network ops before a
single client accepts anything. Also: production consortium needs validator key management,
consensus config, monitoring, backups, upgrades, a block explorer, and on-call — real cost
during a fast-cash lane. Dev-node Besu for demo/pilot; deploy the consortium when a client
co-signs as a validator.
- Reusable competency: the founder is building Besu on the MYR Gas Exchange project — same
skill, possibly shared infrastructure.

### Current code reality (verified 2026-09, ~/lunavsolution-code) — what does NOT exist
- `/share/[token]` → `get_shared_project(share_token)` is a **LIVE** view of current markers.
No snapshot, no version, no "issued at", no record of what the client saw.
- The ONLY client write is `set_marker_client_feedback(p_marker_id, p_comment,
  p_action_needed)` (anon SECURITY DEFINER, autosave 800ms) → per-finding comment +
Action-needed toggle (`markers.client_comment` / `markers.action_needed`).
- **There is NO report-level acceptance anywhere**: no accept/reject, no sign-off, no
`client_accepted_at`, no review status, no versioning, no audit chain.
- `supabase/phase2_approval.sql` is USER approval (admin approves which inspectors may log
in) — do NOT confuse it with client report acceptance.
- No realtime: the inspector only sees client feedback on reload; no notification either way.

### Founder decisions on the chain + acceptance (ANSWERED — do not re-ask)
1. **Consortium, not single-party** — the client and the inspector each run a validator
   node alongside LunaV. See the refinements in the Besu section above.
2. **Acceptance is OPERATIONAL only** (tamper-evidence), never legal. The legal instrument
   stays as paper: PE-signed printed report, accepted by the client. Build a simple signed
   attestation, not a compliant e-signature scheme.
3. **The ASSET entity is the missing anchor** — see the asset-centric subsection above; it
   is an upstream schema change that gates the cross-year record AND the hash chain.

### Open questions still pending from the founder
1. Validator count — stay at 3 (LunaV + owner + firm), or add a 4th neutral party?
2. Small clients — read-only verifier tier, or exclude non-enterprise owners from the
   chain narrative entirely?
3. Assets — flat, or hierarchical (site → component → sub-component)?
4. Does an asset belong to ONE owner forever, or can ownership transfer (asset sold, new
   owner inherits the record)? This changes the chain semantics more than it looks.

## Marker space invariant (READ BEFORE any scale/transform work)
Markers are **world-space siblings**, not children of the model group — they are
placed at the model's rendered surface point and stored as absolute
`position_x/y/z`, added straight to `scene` in `Viewer3D.tsx`. Scaling the model
root AFTER markers exist → surface moves, marker coords stay → **drift**.
Scaling BEFORE any marker exists → zero drift. So any true-size/scale feature
must be a *gate at load time*, not an afterthought on an annotated model.
Full working pattern + pitfalls: `references/model_scale_calibration.md`.

## Adding a new proxy shape (e.g. the Dimension measure tool)
To extend the proxy system with a new `shape`, follow
`references/proxy_shape_extension.md` — schema + types + Viewer3D render block +
toolbox button, with the AutoCAD-style `dimension` line as the worked example.
NOTE: the Dimension tool now lives in its OWN "Dimension Tool" group below the
Spatial Proxy Toolbox (it was moved out of the primitive toolbox on founder
request). The `annotation` shape prototyped earlier was REVERSED and removed.

### PITFALL — dimension must stay DECOUPLED from the Spatial Proxy drawer
The Dimension tool is NOT a "spatial proxy" even though it shares the `proxies`
table/shape union. The founder was explicit: creating a dimension must NOT open
the Spatial Proxy editor drawer. Enforce three things or the association leaks:
- `addDimension` must NOT `setActiveProxyId(...)` after insert (that's what opens
  the drawer) — just append the row and toast.
- The Spatial Proxy drawer render condition must exclude dimension:
  `{activeProxy && activeProxy.shape !== "dimension" && !readOnly && (...)}`
  (only box/plane open the drawer).
- Clicking a dimension in the left proxies list should open its Record tab
  (`setDimensionInput` + `setDimEditor`), not set activeProxyId.

### Dimension visual + record conventions (founder-confirmed)
- Ends are thin AutoCAD-style arrowheads on the line; the DRAG handles are small
  thin diamond grips (`THREE.OctahedronGeometry(0.35, 0)`), NOT bulky
  `SphereGeometry` nodes — the founder rejected the bulky node look. Arrowheads
  are kept SMALL (half the original: `ConeGeometry(0.25, 0.7, 12)`).
- Line + arrowheads + end-ticks + center label render in PALE YELLOW `#e6cf4a`
  — founder asked for "obvious but not obstructing." New dimensions are created
  with `color: "#e6cf4a"`; Viewer3D's `col = p.color ?? "#e6cf4a"` fallback covers
  any dimension that has no stored color. Existing dims keep a previously-saved
  color until cleared.
- The Record tab has a single free-text **Value** field (number + unit typed
  together, e.g. "12.4 m overall width"); the unit selector (m/cm/mm/ft/in) was
  REMOVED. A Note textarea remains. Keep saving `dimension_unit` as `""` so the
  column stays populated for compat; the on-model label shows only the value text.

### PITFALL — deleting a dimension leaves the value text box stuck on screen
`removeProxy` deletes the row and filters it out of state, and the proxy-sync
effect's cleanup calls `scene.remove(obj)` + `traverse(...)` disposing
geometry/materials — so the 3D line, arrowheads, and grips vanish. BUT the
center value label is a `CSS2DObject` whose wrapped `HTMLElement` is NOT detached
by that cleanup, so the text box stays frozen on screen until refresh (founder
bug: "delete doesn't remove the lines and the text box immediately"). Fix the
proxy-sync cleanup loop to also remove each child's CSS2D `element`:
```ts
obj.traverse((c) => {
  if (mesh.geometry) mesh.geometry.dispose();
  /* ...dispose material... */
  const elc = (c as unknown as { element?: HTMLElement }).element; // CSS2DObject
  if (elc && elc.parentNode) elc.parentNode.removeChild(elc);
});
```
Any future proxy/marker render that carries a CSS2D label must include this in
its removal path or the same "ghost label" reappears. Cross-reference the
general Three.js rule in the `react-three-viewer` skill (PITFALL 5).


### PITFALL — new proxy `shape` → HTTP 400 on insert (DB CHECK, not code)
Adding a new `shape` value to the TS union AND `schema.sql` is NOT enough — the
**live** `proxies` table has `check (shape in ('box','plane','dimension'))`, and a
code-only deploy to Vercel never touches it. Inserting the new shape then fails
with `Failed to load resource: 400 () (proxies)` before any column logic runs
(this is exactly what happened with `dimension`). Same class of trap as the
branding-400 / RETURNS-TABLE-42P13 below, but for the proxies table. To ship a new
proxy shape you must hand the founder an idempotent migration that widens the live
CHECK and adds any new columns, e.g.:
```sql
alter table public.proxies drop constraint if exists proxies_shape_check;
alter table public.proxies add constraint proxies_shape_check
  check (shape in ('box','plane','dimension'));
```
- **Don't guard the widening on constraint NAME.** A `if not exists (select 1 from
  pg_constraint where conname='proxies_shape_check' and pg_get_constraintdef(oid)
  like '%dimension%')` guard is fragile — if the live constraint has an
  autogenerated/different name the guard never matches and the migration silently
  does nothing while the founder still sees 400s. Prefer unconditional
  `DROP CONSTRAINT IF EXISTS` + re-`ADD` (idempotent), or verify the applied state
  afterward with `select conname, pg_get_constraintdef(oid) from pg_constraint
  where conname='proxies_shape_check'`.
- The founder may report "applied with success" without that being verifiable —
  give them the verification SELECT above when a 400 persists.
- When the founder later REVERSES a shape, revert the TS union, the schema.sql
  CHECK, and re-scope the migration to the reduced shape set (the annotation
  reversal in this session removed `annotation` from the CHECK and dropped the
  `annotation_text` column from both type and schema).

## Video embeds on a marker/node (YouTube, HTML panel — NOT on-model)
When the founder asks to "attach a video to a node/marker on the 3D Digital Twin,"
the SAFE, CORS-correct answer is an HTML `<iframe>` panel beside the node control —
NEVER a WebGL `CanvasTexture` on the .glb surface.

- A YouTube embed (`https://www.youtube.com/embed/<id>?rel=0`) is an HTML iframe
  overlaid on the page. It does NOT touch the Three.js scene or the .glb, so it adds
  ~no memory/render cost to the model — only the composited frame is drawn. Video
  is NOT memory-unsafe here; the "crash" worry does not apply.
- **Hard constraint:** YouTube blocks canvas readback (tainted canvas), so you CANNOT
  capture YouTube frames into a `THREE.CanvasTexture`/`VideoTexture` plane pinned to
  the model surface — it renders black/blank. There is no clean workaround for YouTube.
- If video genuinely must appear ON the model surface, the source must be a direct
  `.mp4` file (e.g. uploaded to R2), used as a `VideoTexture` on a billboard plane at
  the marker's world position. That is the only CORS-safe on-model path.
- So: source = YouTube link → render in an HTML panel; source = direct video file →
  can be a model-surface texture. Pick based on the founder's source.

### PITFALL — new marker field won't appear in CLIENT/SHARE view
The owner workspace loads markers directly, but the **client/share view loads them
via the `get_shared_project` RPC** (`supabase/20260801_apply_client_feedback_live.sql`),
which builds each marker's JSON with an EXPLICIT column list. Adding a column to
`markers` (e.g. `videos_json`) makes it work for the owner but NOT for clients —
the field is absent and the UI falls back to the empty state ("No Video Attached
Yet"). **Every new marker field must be added to BOTH** the `Marker` type AND the
marker projection inside `get_shared_project` (plus `coalesce(k.<col>,
'[]'::jsonb)` for arrays / a sensible default for scalars), then the RPC re-created
(`create or replace` — the return is jsonb not RETURNS TABLE, so no drop-first
needed). Verify by loading a share link logged-out. Same class of "live RPC omits
column" trap as the branding 400 / RETURNS TABLE 42P13.
- Data model pick for a video list on a marker: a `videos_json: {title,url}[]` column
  on `markers`, mirroring the proven `photos_json` array pattern (fastest — rides the
  existing marker payload, no N+1; RLS-scoped like photos). Reject a separate
  `marker_videos` table for this (slower, more code, zero user benefit).
- Panel placement on the Defect Detail drawer: between the description/remarks and the
  photos grid (matches the founder's "below remarks, above image" ask).
- Memory stays bounded: iframes buffer in chunks; unmount on drawer close; auto-play at
  most 1-2, show thumbnails for the rest.

Full implementation reference (shipped 2026-08-17, commit `4dc7070`): the `videos_json`
column DDL, `src/lib/youtube.ts` validator/embed-converter, drawer placement (owner
`activeMarker` + read-only `detailMarker`), and iframe props — see
`references/marker-youtube-videos.md`.

## Photo evidence — cap, pagination, and Delete placement (2026-08-17)
Markers hold up to **10** photos (`photos_json` array; `MAX_PHOTOS = 10` in
`attachPhotos`, counter shows `/10`). Both the owner edit drawer and the client
"Defect Detail" modal show **2 photos per page** via the shared
`<PhotoPagination page totalPages onChange>` component
(`src/components/PhotoPagination.tsx`):
- Numbered paginator `‹ 1 2 … 5 ›`; arrows AND numbers clickable; current page
  highlighted in turquoise; **hidden entirely when totalPages ≤ 1** (founder option A).
- Ellipsis rule: show all numbers up to 5 pages; beyond that show
  `1 … current±1 … last`.
- Only the current page's `<img>`s are in the DOM (`loading="lazy"`); unvisited pages
  don't fetch. Use a `PHOTOS_PER_PAGE = 2` const + `ownerPhotoPage`/`detailPhotoPage`
  state; **reset to page 1 on marker switch** (useEffect keyed on marker id);
  **auto-step back a page** if deleting the last photo on the current page empties it.
- Grid `grid-cols-1 sm:grid-cols-2` → mobile 1/row, desktop 2/row.
- **Delete Marker button sits BELOW the paginator** behind a separator
  (`mt-5 border-t pt-4`), deliberately separated from the photo flow so it isn't
  accidentally clicked next to photos.

### Destructive marker actions need an in-app confirm modal
Never let Delete Marker fire directly from the drawer button. Gate it behind a
styled in-app confirmation modal (NOT the browser `confirm()` box — the founder
asked for a "confirmation tab" that matches the app). Pattern (shipped 2026-08-17,
commit `b6940c4`):
- `const [confirmDeleteMarker, setConfirmDeleteMarker] = useState(false)`.
- Drawer button sets it true: `onClick={() => setConfirmDeleteMarker(true)}` — it
  must NOT call `deleteMarker()` directly.
- Modal: `fixed inset-0 z-50` overlay with dimmed `rgba(5,7,10,0.72)` +
  `backdropFilter: blur(6px)`; inner `dash-panel` card with
  `onClick={(e) => e.stopPropagation()}` so clicking the overlay closes but the
  card doesn't. Body shows the marker title (`“{activeMarker.title}”`) and warns
  photos/videos/feedback are removed permanently. Buttons: **Cancel**
  (`setConfirmDeleteMarker(false)`) + **Delete permanently** (`onClick={deleteMarker}`,
  `mb-btn-danger`).
- The real `deleteMarker()` sets `setConfirmDeleteMarker(false)` on success.
- Gate the whole modal `{confirmDeleteMarker && activeMarker && !readOnly && (...)}`.
- This is the same "confirm destructive action" discipline already used for
  Company Control Delete in RINA — apply it to any single-click delete in a drawer.

## Zones — pitfalls that cost real time
The invariants, the schema and the implemented panel/report/analytics surface live in
`## Grouping models (zones / sections) — invariants before building` below, with the DDL and the
implementation recipe in `references/model-zones.md`. Read that first; the two traps below are
the ones that actually bit.

### PITFALL — `get_shared_project` must be re-created on the LATEST vintage, not the repo's
`supabase/migrations/` oldest copy. Verify the LIVE function's projection before replacing it:
the anon key can read `project_nodes` (public index) → grab a real `lunav_share_token` →
`POST /rest/v1/rpc/get_shared_project {"share_token":"…"}` and inspect the returned keys. Then
add only the new field (`zone_id`, `zones`, …) on top of what the live function already returns
(`readings`, `videos_json`, `site`). Returns jsonb, so `create or replace` needs no drop-first.

### PITFALL — the version stamp has to be RENDERED, not just bumped
`src/lib/app-version.ts` can be dead code: a release can set `APP_VERSION` while nothing
imports it, so the standing "tag + Release + visible stamp" rule is only half-honoured.
Before claiming a version is stamped, `grep -rn "APP_VERSION" src/` — if the only hit is the
definition, render it.
WHERE: the **GLOBAL footer in `src/app/layout.tsx`**, as one more `| V0.xx` item after the
Privacy / Terms / Cookies links. That is the founder's ask verbatim ("put the version number
at the bottom of the page, place it somewhere next to cookies"), it covers every page (login,
dashboard, client portal), and it is the only bottom strip that is actually visible. Do NOT
park it in the workspace's own bottom rail: that rail sits inside the `h-screen flex flex-col`
shell while the global footer is `fixed inset-x-0 bottom-0 z-50`, so the global footer paints
over the rail and the stamp gets buried — the rail's own Privacy/Terms/Cookies links predate it
and are equally obscured. Using the global footer also makes the stamp verifiable from the CLI
(it is server-rendered, so `curl` sees it).

## Project Homepage analytics panel (V0.22)
The Project Homepage (`/project/[id]/home`) is a full-bleed Leaflet map with floating
panels; before V0.22 it carried NO inspection data (props were only
`projectId/projectName/canEdit/shareToken`), which is why it read as empty.

- **Entitlement reuses the existing privacy boundary.** Owner always sees analytics; an
  anon viewer sees them ONLY with a valid `?share=<token>`. A private project reached from
  R-Tessera without a token stays location-only — pass `stats={null}` and the panel does not
  render. This is why the feature needs NO new anon RPC and no SQL: the share bundle already
  carries every marker's status.
- **Server-computed, one prop.** `ProjectHomepage` is a client component — compute stats in
  `app/project/[id]/home/page.tsx` (owner: session tables; client: `get_shared_project`
  bundle) and pass one `stats` object. Never fetch analytics client-side.
- **One shared computation** — `src/lib/projectStats.ts#computeProjectStats()` (pure, no I/O)
  serves both read paths, so the owner's numbers and the client's can never disagree. It
  derives each marker's zone from its owning model.
- **Panel mechanics:** `data-float="analytics"` (auto-hidden in phone immersive mode), CSS
  `.ph-stats*` in `globals.css`, spawned BESIDE the Project Details card (which is the
  `ph-remarks` panel, bottom-right) — desktop `right:332px; bottom:52px`, ≤1100px moves it
  under the nav, ≤640px becomes a full-width sheet.
- **A donut shows ONE dimension.** Severity gets the ring; the per-zone split must be
  FAIL/WARN/PASS bar rows, rendered only when the project actually uses zones.
- Vocabulary on the client-facing surface: PASS/WARNING/FAIL plus a plain-language legend
  (Critical = FAIL · Attention = WARNING · Compliant = PASS).

### PITFALL — styles scoped to one component's `<style>` block can't be reused
`SeverityBars` originally styled its bars with `.model-bar-track/.model-bar-fill`, defined
inside a `<style>` tag rendered by `ProjectWorkspace`'s analytics tab. A second consumer (the
homepage) got invisible bars. Shared components must style via GLOBAL classes — the pair now
lives in `globals.css` as `.sev-bar-track/.sev-bar-fill`. Same reasoning applies to the
donut/bars themselves: keep ONE copy in `src/components/SeverityVisuals.tsx` (default export
`SeverityDonut` + named `SeverityBars`) and import it everywhere, or the workspace and the
homepage will drift.

### Verifying a server-rendered page from the CLI (no browser, no login)
Next SSRs client components, so a page's initial HTML is greppable. Pull a real
`lunav_share_token` from `project_nodes` with the anon key, then:
```bash
curl -s "$BASE/project/$PID/home?share=$TOKEN" > /tmp/h.html   # grep for the panel + real numbers
curl -s "$BASE/project/$PID/home"            > /tmp/h2.html  # grep must find NO panel
```
That proves BOTH the feature and the entitlement rule from the outside. Strip tags in Python
before grepping text (React inserts `<!-- -->` between adjacent text nodes, so JSX like
`{n} finding{s}` looks like "finding s" in raw HTML).

## Trigger conditions

- User asks about LunaV, lunavsolution, or the LunaV Studio codebase
- User wants to modify the 3D viewer, markers, or model handling
- User asks about the LunaV project architecture

## Project overview

- **Repo**: `kingkymaru-glitch/lunavsolution` on GitHub
- **Local clone (ACTIVE checkout)**: `~/lunavsolution-code` — NOT `~/Documents/ss-rover-cloud`
  (that older folder is the legacy repo name; `git status`/`git log` in `~/lunavsolution-code`
  is the source of truth. The `ss-rover-cloud-dev` skill covers the old folder and flags itself
  deprecated.)
- **Live URL**: `https://lunavsolution.vercel.app`
- **Stack**: Next.js (App Router) + Three.js + Supabase + Cloudflare R2
- **Supabase**: `okzmblyboudjffaifixa` (rover-r-platform, Sydney) under `kingkymaru` account — dashboard: https://supabase.com/dashboard/project/okzmblyboudjffaifixa
- **Purpose**: 3D spatial risk inspection — inspectors upload GLB/GLTF/OBJ models, place inspection markers (points, along-lines, boxes) on the 3D surface, and share audit reports with clients
- **NOTE**: The SIMULATION tab (flood/shadow physics analysis) was REMOVED from LunaV Solutions and ported to ARRAS only. Do NOT rebuild it here — that feature now lives in `~/ARRAS`.

## Admin identity is a HARDCODED EMAIL LIST in SQL, not a column
`public.is_admin()` is a `security definer` SQL function whose body is literally
`u.email in ('inventedmaru@gmail.com', ...)`. There is no `is_admin` boolean on
`profiles`. Consequences:
- Adding an admin means REPLACING that function with the extra address — a schema
  change, so it ships as a bare SQL paste (SQL hand-off rule).
- The list drifts silently: this project's real admin set and the list in the
  function had diverged, so named admins could not open the Admin page or approve
  anyone while the function still returned true for one address.
- `profiles.approved` is a DIFFERENT gate (may this account log in at all).
  `profiles.gpu_access` is a third (may this account run GPU jobs). Do not conflate
  the three; `can_use_gpu()` = admin OR gpu_access.

To answer "who is an admin" or "who owns this", read the live tables with the
service_role key (`/auth/v1/admin/users` for emails, `/rest/v1/profiles` for
flags, `/rest/v1/projects` for `owner_id`) — never infer it from the skill, a
vault note, or a filename. An owner_id is a uuid; join it to an email before
naming a person, and do not guess which account a project belongs to.

## Operating on a shared multi-tenant database — the rules that keep you safe
This Supabase project holds REAL work for several people (several owners, each
with their own projects). Anything you write is visible to a human who did not ask
for it.
- **Never attach a test artifact to a project you do not own.** Do not grab "the
  first project" from a query as a scratch target — that writes junk into someone
  else's data. Create a throwaway project, or ask which target to use.
- **Never delete from an account that is not the user's.** If test output has
  already landed in another person's project, DUPLICATE it to the intended place and
  leave the original alone. Cleanup by deletion is not yours to perform there; say so
  and let the owner remove it.
- **Judge a credential by a live call, never by its appearance.** A key passed
  through a rich-text editor can DISPLAY as elided (`eyJhbG..._7_8`) while the stored
  string is complete — decode it (a JWT payload shows `ref` + `role`) and make one
  real authenticated request before declaring it invalid. The inverse also holds:
  looking well-formed is not proof. Corollary: a BUCKET NAME is a readable word; if a
  field that should be a name looks like a 64-char hex digest, the export wrote hashes
  into the fields and none of those values are usable.

## Supabase account landscape

LunaV has its OWN Supabase project. Do NOT confuse with other apps:

| Account | Project Ref | App |
|---------|------------|-----|
| kingkymaru | `okzmblyboudjffaifixa` | **LunaV** (rover-r-platform, Sydney) |
| kingkymaru | `joliwavzczzfiwpwrbtf` | RINA (Sydney) |
| inventedmaru@gmail.com | `merfmrlkjoqrhijzfwbn` | AnglerGO |
| inventedmaru@gmail.com | `atfmtstxfxulrbpsbpav` | r-tessera |

No sharing — each app has its own Supabase instance. Both `kingkymaru` and `inventedmaru@gmail.com` are at the 2-project free cap.

## Button scale, sliders, UI density
`.mb-btn` is the shared button class — one `globals.css` edit restyles the whole app.
Tier table, label-band rule, "width comes from the LABEL", override inventorying, 44px
tap-target guard, geometry verification: `references/ui-button-scale.md`. Slider recipe
+ `getComputedStyle` pseudo-element trap: `references/ui-range-sliders.md`.
Density (inputs, tables, alignment): `references/ui-density-and-button-system.md`.
Always-on:
- A modifier must follow its base in `globals.css`, or use a compound selector
  (`.mb-input.mb-input-sm`) — equal specificity resolves by source order, and a
  silently-ignored modifier is the failure mode.
- A `<colgroup>` using `readOnly ?` has PER-VARIANT widths — rebalance and verify
  BOTH variants; the read-only view's extra column has its own control that can
  breach just like a pill.
- Verify density at the table's `minWidth` floor, not the browser width.
- Bump `APP_VERSION` in the same commit, then grep the SERVED page for the stamp
  before pushing.

## Key files

| File | Purpose |
|---|---|
| `src/components/Viewer3D.tsx` | Pure Three.js 3D renderer — model loading, marker rendering, raycaster interaction |
| `src/app/dashboard/page.tsx` | Inspector dashboard — project list, search, sort, grid/list toggle (severity filter REMOVED — now on Audit Report tab) |
| `src/components/ProjectWorkspace.tsx` | Main cockpit — model CRUD, marker CRUD, tabs (3D/Report/Analytics/Docs/Studio), severity filter on Audit Report, ⚙ Settings dropdown (Export Link / Appearance / Logout) |
| `src/lib/types.ts` | All TypeScript types: Marker, Model3D, ProxyShape, MarkerKind, etc. |
| `src/lib/gltf-pack.ts` | Converts split glTF (.gltf + .bin + textures) into single .glb for upload |
| `src/lib/r2-upload.ts` | Direct browser-to-R2 upload with presigned URLs |
| `src/lib/r2-list.ts` | Client helper calling r2-list edge function for LUNASCAN import |
| `src/components/ImportScanModal.tsx` | Modal to browse + import LUNASCAN .glb scans from R2 |
| `supabase/functions/r2-list/index.ts` | Edge function: list R2 objects by prefix, auth-gated |
| `supabase/functions/r2-presign/index.ts` | Edge function: presigned PUT URLs for browser upload |
| `supabase/migrations/` | Idempotent SQL migrations (run manually in SQL Editor) |
| `src/lib/supabase/client.ts` | Browser-side Supabase client |
| `src/lib/supabase/server.ts` | Server-side Supabase client |
| `supabase/schema.sql` | Full DB schema |

## Architecture: how markers attach to GLB models

### Data model

- `Model3D`: `id`, `file_url` (R2), `file_ext` (glb/gltf/obj), `model_name`, `source` (`manual` | `lunascan`), `file_size_bytes`, `position_*`, `rotation_*`
- `Marker`: `model_id` → Model3D, `position_x/y/z` (world-space), `kind` (point/along/box), `geometry_json` (extra shape data)

### 3D rendering (Viewer3D.tsx)

1. **Model loading** (lines 315-362): Model is loaded via `GLTFLoader`/`OBJLoader` from R2 URL. The `place()` function auto-centers the model (`Box3.getCenter`) and uniformly scales it to fit a 25-unit bounding box (`scale = 25 / Math.max(size.x, size.y, size.z)`).

2. **Marker placement**: Markers are NOT parented to the model group — they are added directly to the scene as siblings. Their world-space coordinates (`position_x/y/z`) are absolute.

3. **Click-to-create**: When `addMarkerMode` is armed, a raycaster fires against `modelGroupRef.current.children` (the loaded model mesh). The intersection point's world-space coordinates become the marker's `position_x/y/z`.

4. **Marker rendering** (lines 364-493):
   - **Point**: `CSS2DObject` (HTML div pin) at world coords, colored by status
   - **Along**: `TubeGeometry` through `CatmullRomCurve3` of geometry points, with spheres at vertices
   - **Box**: `LineSegments` wireframe box with offset/rotation, plus 0.08-opacity fill

### Marker kinds

| Kind | Description | Key fields |
|---|---|---|
| `point` | Single inspection pin | `position_x/y/z` |
| `along` | Curved line along a path | `geometry_json.points[]`, `thickness`, `color`, `dash` |
| `box` | 3D bounding box defect | `geometry_json.size`, `offset`, `rotation`, `color`, `dash` |

## RPC patterns for search / filter / sort

When building dashboard search or filter features, use a **single Supabase RPC function** that joins across tables and returns enriched rows. Avoid N+1 client-side queries or Supabase client joins — one RPC call is faster and keeps filtering server-side.

### Template

```sql
create or replace function public.function_name(
  p_search   text default null,
  p_filter   text default null,
  p_sort     text default 'updated'
)
returns table( /* enriched columns */ )
language sql
security definer set search_path = public
stable
as $$
  with enriched as (
    /* join projects → models → markers with counts/averages */
    select ...
    where owner_id = auth.uid()    -- RLS equivalent
    group by ...
  )
  select * from enriched e
  where
    (p_search is null or e.name ilike '%' || p_search || '%')
    and (p_filter is null or ...)
  order by case when p_sort = 'x' then ... end
  ;
$$;

grant execute on function public.function_name(text, text, text) to authenticated;
```

Key conventions:
- Parameter prefix `p_` to avoid name collisions with columns
- `security definer` + `auth.uid()` for RLS-equivalent scoping (the function runs as owner, no extra RLS policies needed)
- `stable` volatility — safe for read-only queries with `auth.uid()`
- `case` expressions for dynamic sorting (Postgres can't parameterize ORDER BY directly)
- Always `create or replace` — idempotent, safe to re-run
- Save in `supabase/migrations/<timestamp>_<name>.sql`
- Run manually in Supabase SQL Editor → paste + run

### Live example: `search_projects` dashboard RPC

`supabase/migrations/20260805_search_projects.sql` — joins `projects → models → markers`, returns enriched `ProjectCard` rows with `model_count`, `fail_count`, `warning_count`, `pass_count`, and `updated_at` (greatest of project/model/marker timestamps). Supports `p_search` (ILIKE project_name + model_name), `p_severity` (FAIL/WARNING/PASS filter), `p_sort` (updated/name).

See `references/search-projects-rpc.md` for the full SQL.

### TypeScript contract

Define a matching interface in `src/lib/types.ts` for the RPC return type, plus filter/sort/view type aliases:

```ts
export interface ProjectCard {
  id: string;
  project_name: string;
  created_at: string;
  updated_at: string;
  client_share_token: string | null;
  model_count: number;
  fail_count: number;
  warning_count: number;
  pass_count: number;
}

export type SeverityFilter = "FAIL" | "WARNING" | "PASS" | null;
export type ProjectSort = "updated" | "name";
export type ViewMode = "grid" | "list";
```

Call it from the client with `supabase.rpc("search_projects", { p_search, p_severity, p_sort })`.

**Note (2026-08-05):** the dashboard homepage no longer uses `p_severity` — it always passes `null`. The severity filter was moved to the Audit Report tab where it actually helps inspectors triage findings. The RPC still supports the parameter; only the dashboard consumer changed.

## Audit Report — severity filter + per-defect timestamps

The Audit Report tab (inside `ProjectWorkspace.tsx`, `tab === "report"`) lists all inspection markers across all models. Two features were added on 2026-08-05:

### Severity filter pills

```tsx
const [reportFilter, setReportFilter] = useState<"ALL" | MarkerStatus>("ALL");

const filteredMarkers = useMemo(
  () => reportFilter === "ALL" ? allMarkers : allMarkers.filter((m) => m.status === reportFilter),
  [allMarkers, reportFilter],
);
```

Filter pills render as a button bar above the table:
```tsx
{(["ALL", "PASS", "WARNING", "FAIL"] as const).map((f) => (
  <button onClick={() => setReportFilter(f)} className={reportFilter === f ? "mb-btn-primary" : ""}>
    {f !== "ALL" && <span className="inline-block h-2 w-2 rounded-full" style={{ background: STATUS_COLOR[f] }} />}
    {f}
  </button>
))}
```

The table renders `filteredMarkers` instead of `allMarkers`. When `reportFilter` is "ALL", all markers show. Otherwise only markers matching the selected status appear.

### Timestamp column

Each `Marker` row has `created_at` (ISO string). The table added a "Time" column between Severity and Findings:

```tsx
<td className="px-5 py-4 text-[0.68rem]" style={{ color: "var(--txt-tertiary)" }}>
  {new Date(m.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
</td>
```

This shows e.g. "5 Aug 2026" — inspectors can now sort through recent defects at a glance. For the full datetime format (e.g. "5 Aug 2026, 14:30"), add `.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })`.

See `references/audit-report-filter-pattern.md` for the full implementation checklist.

## Topbar settings dropdown pattern

When the topbar accumulates too many discrete buttons (Export Link, Appearance, Logout),
consolidate them into a single ⚙ Settings dropdown. Pattern:

```tsx
const [settingsOpen, setSettingsOpen] = useState(false);

/* Close on outside click — must stopPropagation on the toggle button */
useEffect(() => {
  if (!settingsOpen) return;
  const close = () => setSettingsOpen(false);
  document.addEventListener("click", close);
  return () => document.removeEventListener("click", close);
}, [settingsOpen]);
```

```tsx
<div className="relative">
  <button
    onClick={(e) => { e.stopPropagation(); setSettingsOpen((o) => !o); }}
    className={`mb-btn ${settingsOpen ? "mb-btn-primary" : ""}`}
  >
    ⚙ Settings
  </button>
  {settingsOpen && (
    <div className="absolute right-0 top-full z-50 mt-1 w-44 overflow-hidden rounded-lg border"
         style={{ borderColor: "var(--hairline)", background: "var(--dash-panel)" }}>
      <button onClick={() => { setSettingsOpen(false); shareWithClient(); }}>
        📤 Export Link
      </button>
      <button onClick={() => { setSettingsOpen(false); setAppearanceOpen(true); }}>
        🎨 Appearance
      </button>
      <div style={{ borderTop: "1px solid var(--hairline)" }} />
      <button onClick={() => { setSettingsOpen(false); signOut(); }}
              style={{ color: "var(--mb-red)" }}>
        ⏻ Logout
      </button>
    </div>
  )}
</div>
```

**Pitfalls:**
- **`stopPropagation` is essential** on the toggle button — without it, the document click
  handler fires on the same click and re-closes the dropdown immediately.
- Don't use a `ref` + `contains()` approach for outside-click — it breaks when the dropdown
  contains portals or the click target is removed mid-render.
- Each dropdown item must call `setSettingsOpen(false)` before its action, or the dropdown
  stays open after navigation.
- Use a `<div style={{ borderTop: … }} />` separator between normal actions and destructive
  ones (like Logout — shown in `var(--mb-red)`).
- **PITFALL — dropdown covered by the next card (backdrop-blur stacking context).** If the
  card/panel holding the toggle uses `backdrop-blur` (or `filter`/`transform`/`opacity`),
  it creates a CSS **stacking context** that traps an absolutely-positioned dropdown inside
  it: opening downward lets the next sibling card paint over the menu; opening upward clips
  against the panel/container border. **Fix: render the menu in NORMAL document flow** (a
  block below the action row, fixed width, right-aligned) so the card grows to hold it — no
  overlap, no clipping, no z-index fight. Verified on RINA's Company Control cards
  (backdrop-blur-md). Same trap applies to any glassmorphic card carrying a dropdown.
  The same rule bites HARDER inside a scroll container: a menu placed inside the
  `overflow-y-auto` Project Models panel is clipped by that scrollport no matter what
  z-index it carries, so render row-level menus (e.g. the zone "Move/Reuse" menu) as a
  block in NORMAL flow directly under their row — the row grows to hold it and nothing
  clips. Reserve `position: absolute` menus for containers that do not scroll.

### Deep-linking INTO the workspace (`?settings=1` auto-opens the gear dropdown)
The workspace accepts TWO searchParams deep-links, both read in `src/app/project/[id]/page.tsx`
and passed as props to `ProjectWorkspace`:
- `?tab=` → `initialTab` (3d|report|analytics|docs|studio — see nav convention above).
- `?settings=1` → `initialSettingsOpen` — auto-opens the ⚙ Settings dropdown on mount.

Pattern (shipped 2026-08-10, commit `8cb4c26`):
```tsx
// page.tsx
const { tab: tabParam, settings: settingsParam } = await searchParams;
const initialSettingsOpen = settingsParam === "1";
// ...
<ProjectWorkspace initialTab={initialTab} initialSettingsOpen={initialSettingsOpen} />
```
```tsx
// ProjectWorkspace.tsx — mount effect, MUST gate on !readOnly
useEffect(() => {
  if (initialSettingsOpen && !readOnly) setSettingsOpen(true);
}, [initialSettingsOpen, readOnly]);
```
- The Project Homepage Settings button routes `/project/${id}?settings=1` (NOT bare
  `/project/${id}`) so the gear opens without an extra click.
- **Always gate on `!readOnly`** — the client portal has no Settings chrome; an un-gated
  auto-open would set state for a dropdown that must not render there.
- Works alongside the existing outside-click-close effect (the dropdown closes on first
  click elsewhere, which is fine).

**PITFALL (2026-08-10, "LunaV Studio button is dead") — same-route `router.push` does NOT
remount the workspace.** The Settings → LunaV Studio entry used to do
`router.push(\`/project/${id}?tab=studio\`)`. You are ALREADY on `/project/[id]` when you
open Settings, so Next.js performs a same-route navigation: the client component is NOT
remounted and `useState(effectiveInitialTab)` never re-initializes — `tab` stays `3d` and
the studio view never renders. The button looks completely dead (no error, no nav).
**Fix (commit `6bfe6d6`):** since the workspace is already mounted, switch the tab state
directly — `onClick={() => { setSettingsOpen(false); setTab("studio"); }}` — identical to
every other tab button. Rule: for deep-links whose target lives INSIDE the currently
mounted component, call the state setter; reserve `router.push(?tab=...)` for navigation
FROM a different page (e.g. Project Homepage → workspace, where a fresh mount occurs).
Symptom family: "button did nothing" on an in-workspace nav item = same-route push, not a
middleware 307 and not a popup-blocker (check those only after ruling this out).

A `↻` replace button sits next to the `✕` remove button on each model in the sidebar. Clicking it opens a file picker; the selected GLB/GLTF/OBJ is uploaded to R2, then the existing model row's `file_url` and `file_ext` are updated in Supabase. The model **keeps its ID**, so all markers stay attached.

This is lossy for bounding-box-sensitive projects: the original model's auto-centering+scaling isn't stored, so swapped markers won't be perfectly aligned unless the replacement model has near-identical bounding box dimensions. For projects where absolute precision matters, store the original `Box3` with the model and apply a correction on swap.

## Marker position adjustability

All marker kinds now have X/Y/Z position sliders in the detail drawer (`Position (World Units)` section, range -50 to +50, step 0.1). The `savePosition(axis, value)` wrapper handles per-kind behavior:

| Marker kind | Sliders? | Behavior |
|---|---|---|
| Point | X/Y/Z | Moves `position_x/y/z` — pin relocates immediately |
| Along | X/Y/Z | Moves `position_x/y/z` AND delta-shifts all `geometry_json.points` so the entire tube translates |
| Box | X/Y/Z | Moves `position_x/y/z` (center); works alongside existing offset/rotation sliders |

## Multi-model support (current state: single-model only)

Blockers:
- `modelGroupRef` is a single ref, not a map
- `disposeModel()` removes the only model before loading a new one
- `activeModelId` is a single string
- `Viewer3D` receives single `modelUrl` prop
- Markers passed are `activeModel?.markers` (one model's markers only)

## Grouping models (zones / sections) — invariants before building
Founder ask pattern: on a LARGE site the inspector splits the job into sections/rooms, so
many `.glb` scans land in one project and the models list, the audit report, and the
analytics all need to slice by that grouping.

Current surface (verify against the repo — it moves):
- `models` is project-scoped: id, project_id, model_name, file_url, file_ext, source,
  transform (`position_*`/`rotation_*`), scale (`scale_set`/`scale_*`), plus
  `zone_id` (nullable FK → `model_groups`). A `(m.zone_id ?? null)` read keeps rows that
  predate the column valid.
- The "Project Models" panel is a zone TREE: collapsible zone header rows (name ·
  placement count · ↑ ↓ ✎ ✕) with placement rows nested under each, Ungrouped last,
  `+ New Zone` above the model upload, and a per-row `⇄` menu (Move to zone / Reuse in
  another zone). A row click still only sets `activeModelId`.
- A **Zone scope dropdown** above the list (`zoneFilter`: `"all" | "ungrouped" | <zone id>`)
  narrows the panel and snaps `activeModelId` into scope — with the viewer rendering a
  single model, that state snap IS the viewer scope. Reset it back to `"all"` when the
  scoped zone is deleted, or the panel renders permanently empty.
- Audit Report = zone SECTIONS (collapsible header row per zone carrying FAIL/WARN/PASS
  subtotals) plus severity pills AND a Zone dropdown, the two filters ANDed. Flatten once
  into `allMarkers` carrying `modelName` + `zoneId`/`zoneName` (`models.flatMap(...)`), and
  gate the section headers on `zones.length > 0` so zone-less projects and the
  not-yet-projected client portal render exactly as before.
- Analytics = severity strip + per-day time series + both bar blocks, all driven by ONE
  `analyticsZoneFilter` (`"all" | "ungrouped" | <zone id>`): a zone scope selector in the
  header narrows the strip, the series and the bars together, a ZONE BREAKDOWN card sits
  above the per-model card (ordered by `sortedZones`, Ungrouped last) so the page reads
  zone → model. Keep the strip's project-wide `counts` for the 3D-tab severity donut and
  compute a SEPARATE `scopedCounts` for analytics — reusing one object skews the donut.
- Per-model bars are built from a Map **keyed by `model_id`, never `model_name`**: two
  placements sharing a display name (exactly what "reuse this .glb in another zone"
  produces) silently merge into one bar. Also share one `SeverityBars` component between
  the zone and model blocks so the two bar renderings cannot drift.
- Shipped state to check against: the zone projection inside `get_shared_project`
  (`zone_id` on each model + a top-level `zones` array, re-created on the LATEST vintage —
  see the `get_shared_project` vintage pitfall above) is committed and handed to the founder as bare SQL. A code-only
  deploy does NOT apply it, so the client portal keeps rendering flat until they run it —
  which is exactly why every zone surface is gated on `zones.length > 0`. The version
  stamp/tag/Release for the feature is part of the same ship, not a later task.
- There is NO PDF/print exporter in the workspace. The "report" is the on-screen tab plus
  the `/share/<token>` client portal — never promise a PDF that does not exist.

Invariants any grouping feature must hold:
- **ONE FILE, MANY PLACEMENTS (the load-bearing decision).** A repeated structure that
  appears as a DIFFERENT asset in another zone must be a SECOND `models` row sharing the
  same `file_url` — never one row referenced by two zones. Markers hang off `model_id`, so
  a shared row would show the same findings under both zones and DOUBLE-COUNT them in
  analytics. "Reuse in another zone" = copy the row (project_id, model_name, file_url,
  file_ext, file_size_bytes, source, zone_id) with `markers: []`; no R2 re-upload, no
  extra cost. Keep it a distinct action from "Move to zone" (same row relocates) and tell
  the user the new placement starts with 0 pins. Founder chose empty-over-copy-pins.
- **A placement lives in exactly ONE zone.** `models.zone_id` is the column (NOT
  `group_id`). Table = `model_groups` (project_id, name unique per project, sort_order,
  created_at), `zone_id` nullable FK with **`on delete set null`** so deleting a zone
  re-buckets its placements instead of cascading them away; `null` = an "Ungrouped" bucket
  that always exists, always renders last, and cannot be deleted. A plain `zone_name` text
  column loses rename-once, ordering, and empty-zone rendering.
- **Zone is DERIVED, not stored per pin.** A marker's zone comes from `marker.model_id →
  models.zone_id`. Never add a zone column to `markers` — one pin cannot honestly live in
  two rooms.
- **Type it OPTIONAL.** `zone_id?: string | null` on `Model3D` — a required field breaks
  the share-RPC JSON path and any `.insert()` that doesn't set it. Local reads of raw rows
  predating the migration must stay valid (`(m.zone_id ?? null)`).
- **Fail soft when the migration is unrun.** Wrap the `model_groups` query so an error
  yields `zones: []` (log it) instead of throwing — the panel then behaves exactly as
  before, with no zone UI, so a code-only Vercel deploy never breaks the workspace while
  the founder's SQL is still pending.
- Assignment UI = DROPDOWN ("Move to zone…"), never an inline list — founder's picker rule.
- Grouping must NOT imply multi-model 3D render — see the single-model blockers above.
  Rendering a whole zone at once is a separate, much larger feature; keep this a
  scoping/filter lens.
- Add the group fields to the model projection inside `get_shared_project` too, or the
  client portal silently shows everything ungrouped — same explicit-column-list trap as a
  new marker field.
- Schema changes reach the live DB only by the founder pasting bare SQL (SQL hand-off rule
  above); a code-only Vercel deploy never touches the schema.

Settled UI shape (founder-approved): the "Project Models" panel becomes a TREE — collapsible
zone header rows (name · placement count · ↑ ↓ ✎ ✕) with placement rows nested under each,
Ungrouped last; `+ New Zone` control above the model upload; zone assignment via a per-row
`⇄` menu offering both "Move to zone" and "Reuse in another zone"; zone delete behind the
in-app confirm modal (never the browser box) that states placements are KEPT. Report gains
zone SECTIONS (collapsible, per-zone FAIL/WARN/PASS subtotals) plus a Zone filter dropdown
ANDed with the severity pills; Analytics gains a zone scope selector and per-zone bars above
the per-model bars. A sidebar zone-filter mode ("> All zones" → one zone scopes the list and
snaps the active model into that zone) ships in the SAME version. Never fold multi-model
simultaneous render into this work.

### PITFALL — editing `ProjectWorkspace.tsx` (3.5k+ lines): anchor patches, trust `tsc`
Multi-anchor JSX edits in this one giant component go wrong in two predictable ways:
- **The inline LSP diagnostics lie mid-edit.** After a patch lands, they can report
  `JSX element has no corresponding closing tag`, `Cannot find name 'm'`, or
  `',' expected` from a partially-applied parse state — one edit reported 25+ phantom
  errors and `npx tsc --noEmit` then passed clean. Make `npx tsc --noEmit` the authority;
  do not start "fixing" non-errors the diagnostics describe.
- **A JSX block comment must close `*/}`.** Writing `{/* note */` (missing the brace) breaks
  the enclosing element silently and surfaces as a parse error far below the real line.
- **Shared derived state must be declared ABOVE its consumers.** Expect
  `Block-scoped variable 'X' used before its declaration` when a memo added in the report
  section reads one defined further down with the zone helpers — hoist `sortedZones` and the
  flatten memo to the top of the component, next to the state they derive from.

Full schema DDL, the panel-tree implementation recipe, the CTE/flatten changes for the
report, and the chunk-by-chunk build order: `references/model-zones.md`. The living build
plan (authority for locked decisions, one chunk per turn) is the founder's vault note
`Projects/LunaV — Action Plan.md` — read it before resuming this feature.

## LUNASCAN R2 import seam (Phase 6)

LUNASCAN is a standalone CLI (Apple Silicon only, `kingkymaru-glitch/LUNASCAN`) that turns drone video into `.glb` 3D models. The import seam lets inspectors browse LUNASCAN outputs in R2 and import them into LunaV with one click.

### Flow

1. Inspector runs `python -m lunascan.pipeline --video drone.mp4 --r2-upload --r2-bucket <bucket> --r2-prefix job-2026-08-05/`
2. `.glb` + `manifest.json` land in R2 under the prefix
3. In LunaV ProjectWorkspace → "Import from R2" button → `ImportScanModal`
4. Modal calls `r2-list` edge function → lists scan groups (paired .glb + manifest)
5. Click "Import" → inserts `models` row with `source: 'lunascan'` → model appears in viewer

### Key components

- **Edge function** `r2-list`: auth-gated (inspector + approved), uses `@aws-sdk/client-s3` `ListObjectsV2`, groups by directory prefix. Needs secrets: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.
- **DB column** `models.source`: `text not null default 'manual' check (source in ('manual', 'lunascan'))`. Added via idempotent migration `supabase/migrations/20260805_lunascan_import.sql`.
- **Types**: `ScanGroup`, `R2Object`, `R2ListResponse` in `src/lib/types.ts`.
- **UI**: `ImportScanModal.tsx` — fetches scans, shows GLB info + manifest details, one-click import button per scan.

See `references/lunascan-import-seam.md` for detailed implementation notes.
See `references/deploy-checklist.md` for the full deployment procedure.

## Project Homepage (`/project/[id]/home`) — Leaflet 2D satellite map (NOT Cesium)

The bird's-eye context view renders a **Leaflet 2D ESRI satellite map**, NOT a Cesium
globe. The earlier Cesium approach (loaded from CDN to dodge the `\\0`-in-template-literal
SyntaxError) was abandoned: the CDN build had race conditions with React's useEffect
(`flyTo` fired before the viewer loaded → blank), and the founder wanted a simpler
2D map. Use **Leaflet** here. Full technique in the `nextjs-supabase-geo-maps` skill
(CDN loader, `100dvh` flex layout, draggable-rectangle area selection, z-index pitfalls).

### Key homepage specifics (learned the hard way)
- **Pin is the center of truth.** `loadNodeCenter(projectId)` reads the R-Tessera
  `project_nodes` row (one per project, `ON CONFLICT (lunav_project_id)`). The homepage
  center MUST always be re-seeded from that pin on every load — do NOT keep a stale
  `center_lon/lat` saved in `project_sites`, or a previously-drawn area polygon's
  centroid will override the fresh pin and the map shows the wrong location.
- **Globe/map container needs `z-index: 1`** so the `z-index: 5` remarks card and draw
  tools paint ABOVE it (otherwise the map covers the Project Details panel).
- **PITFALL (2026-08-12): a bottom railing/footer inside the 100dvh flex shell can
  render but be CLIPPED off-screen.** The Project Homepage root is
  `<div className="dash-bg flex flex-col" style={{height:"100dvh"}}>` wrapping a
  `<main className="ph-page">` (`ph-page { height:100vh; overflow:hidden }`). When the
  map area (`.ph-shell`) used `height:100%` it grabbed the FULL column height and
  pushed the `<footer>` below the viewport — build passes, DOM has it, nothing shows.
  **Fix that worked:** give `.ph-shell { flex:1 1 auto; min-height:0; }` (NOT height:100%)
  so the footer gets its share of the column. If even that fails, make the footer
  `position: fixed; bottom:0; left:0; right:0` (top-layer, above the absolutely-
  positioned map) and lift any `position:absolute; bottom:Npx` overlays (remarks card,
  save indicator) to `bottom:52px` so they sit above the fixed bar. This mirrors the
  same fix applied to R-Tessera (see r-tessera-dev "PITFALL — bottom railing invisible").
  When adding the LunaV-family footer to the homepage, COPY the workspace footer
  verbatim (teal dot + "LunaV Studio — 3D Engine Online" · "LUNAV STUDIO — ROVER-R")
  and swap the brand string as needed; do NOT invent a new centered-pill style.
- **Always mount the map container** — render loading/error as overlays, never
  `return <Loading/>` before the `<div ref={containerRef}>` is in the DOM, or Leaflet
  initializes against a null container and stays blank. Call `map.invalidateSize()`
  after load.
- **Area-of-works = draggable rectangle, not click-to-draw.** Replace the click-polygon
  flow (it fights Leaflet's pan-drag → "button does nothing"). Drop an `L.rectangle`
  on draw-start, let the user drag/resize, then `confirmRect` reads `getBounds()` →
  GeoJSON ring. See `nextjs-supabase-geo-maps`.
- **Owner-only controls gated by `canEdit`.** All draw/note/delete/edit affordances
  render inside `{canEdit && (...)}` — anon (client/share view) sees the map + saved
  areas + notes read-only, never the edit buttons. The "Upload area .glb" control and
  the "Import from LUNASCAN" button were REMOVED (2026-08-10) per founder; area data
  is now persisted as `area_polygons` jsonb + `annotations` jsonb only.
- **Collapse draw tools into a top-right icon when idle.** Owner draw controls
  (Box/Trace/Note/Delete-all) hide behind a turquoise `✎` button top-right; clicking
  opens the palette. While actively drawing/tracing/noting, controls show inline
  (never hide mid-edit). Pattern: `toolsOpen` state + `.ph-tools-toggle` / `.ph-drawtools-wrap`
  CSS in globals.css. Keep the palette visible during active `drawMode`/`annoDraft`.
- **Basemap toggle (added 2026-08-12):** the homepage has a Map (OSM) / Satellite (Esri)
  segmented control top-left; Satellite is the fronting default. Swap ONLY the Leaflet
  tile layer (`removeLayer` + re-add) via a `tileRef` — never re-create the map, so all
  polygons / node pin / annotations / draw boxes persist intact. Exact code +
  gotchas: `references/leaflet-basemap-swap.md`.
- **Anon nav hardening:** top nav shows ← Back always; ⌂ Home redirects to `/login`
  for anon (visible but routes to login); 🔍 Open Inspection is `canEdit`-gated (hidden
  for anon). This lets an R-Tessera peek land on a read-only report with no edit escape.
- **Nav arrangement is THREE-ZONE and must match across pages (standardized 2026-08-10).**
  Left cluster: logo + product name + (owner) Home · Project Home (active/primary) |
  (anon) ← Back · Home. Center flex group (`overflow-x-auto`): the tab buttons
  (3D Digital Twin / Audit Report / Analytics / Documents). Right cluster: Settings
  (owner) or the "Client View — Read Only" chip (anon). The **Project Homepage
  (`/project/[id]/home`) was refactored to mirror this exact layout** so it reads like
  every other page — its `canEdit` branch renders Home · Project Home (disabled/primary)
  · then the center tab group links to `/project/[id]?tab=3d|report|analytics|docs` ·
  then Settings (right). Anon branch: ← Back · Home (→/login), no tab group, read-only chip.
  Pattern: use the same `mb-btn` / `mb-btn-primary` styling and three flex clusters as
  `ProjectWorkspace`'s nav; do NOT cram all buttons into one left-aligned inline row.
- **Settings dropdown carries a "LunaV Studio" entry (2026-08-10).** The workspace ⚙
  Settings dropdown items are: Export Link · Appearance · **LunaV Studio** (opens the
  3D Model Builder — see same-route pitfall below) · Logout. The standalone "LunaV
  Studio" *tab* was removed from the top tab row (owner now lands on 3D Digital Twin),
  but the entry lives INSIDE Settings so it isn't lost. Add new top-level destinations
  as Settings-dropdown entries, not new nav tabs, to keep the tab row short.
- **All button labels are TEXT-ONLY (no leading emoji/icon glyphs) since 2026-08-10.**
  Founder standardized: strip `⌂ 🌐 🧊 📋 📊 📁 ⚙ 📤 🎨 ⏻` etc. from every nav tab + Settings
  dropdown entry. Keep functional in-canvas controls (draw-tools ✎/▭/✏️/📝/🗑, × close)
  iconed — those are map tools, not nav/settings. When adding a nav/Settings button, use
  the plain name (e.g. "3D Digital Twin", not "🧊 3D Digital Twin").

## Themes (Appearance → Theme) — adding "Glass" (2026-08-10)

Themes are a typed union `brand_theme: "dark" | "light" | "midnight" | "glass"` (see
`src/lib/types.ts` — both `Project.brand_theme` and `ClientBranding.theme`). They apply
via `data-theme` on `<html>` (set in `ProjectWorkspace`), driving CSS custom properties
in `src/app/globals.css` (`html[data-theme="..."]` blocks).

**Glass theme = iOS-style frosted glassmorphism:** highly translucent `rgba()` surfaces
(`--dash-panel`/`--dash-panel-raised` ~0.55 alpha), iOS system-blue `#0a84ff` primary +
`#5ac8fa` cyan, airy light text `#f2f5ff`, soft blue glow. Add a new theme by:
1. Append an `html[data-theme="<name>"] { ... }` block in `globals.css` (copy the `dark`
   block, swap the rgba/hex values). Don't delete/reorder other theme blocks.
2. Add `"<name>"` to the union in `types.ts` (2 spots) + `ProjectWorkspace` (3 `theme`
   type spots) + both page casts in `share/[token]/page.tsx` and `project/[id]/page.tsx`.
3. Add `"<name>"` to the appearance selector list
   `([\"dark\",\"light\",\"midnight\",\"glass\"] as const)` in `ProjectWorkspace`'s
   Appearance panel.
4. **DB gotcha:** `projects.brand_theme` has a `CHECK (brand_theme IN ('dark','light',
   'midnight'))` constraint — adding a value WITHOUT extending the CHECK makes
   `saveBranding({theme:'glass'})` fail silently/error. Ship a migration that
   `DROP CONSTRAINT IF EXISTS projects_brand_theme_check` then re-adds it with the new
   value, ending in `NOTIFY pgrst, 'reload schema';`. (See `supabase/migrations/
   20260809_glass_theme.sql` for the exact form.) This is the SAME class of trap as
   P45/P47 in `supabase-backend` — a new enum-style value needs both the TS union AND
   the live CHECK updated, or the write is rejected.

 ## Diagnosing a live RPC 400 ("update_project_branding" 400s) — probe, don't assume

 Symptom: browser console shows `Failed to load resource: 400 (update_project_branding)`
 when saving branding/theme. **Do NOT assume the function is missing** — a missing/mismatched
 function gives PGRST202, but a 400 with the body running means a runtime error INSIDE the
 function (most often the CHECK constraint above). Distinguish them with a live anon probe
 using the R-Tessera hardcoded anon key (same backend `okzmblyboudjffaifixa`,
 `~/Documents/R-Tessera/src/lib/supabaseClient.js`):

 ```bash
 KEY=$(grep -o "eyJ[A-Za-z0-9_.-]*" ~/Documents/R-Tessera/src/lib/supabaseClient.js | head -1)
 URL="https://okzmblyboudjffaifixa.supabase.co/rest/v1/rpc"
 # no args -> PGRST202 "Could not find the function" = absent/wrong signature
 curl -s -X POST "$URL/update_project_branding" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
 -H "Content-Type: application/json" -d '{}'
 # exact client args (bogus uuid) -> P0001 "Not project owner" = function EXISTS, body ran;
 # the ownership check fires first for anon, which is EXPECTED — 400 is then a runtime
 # error inside the UPDATE (CHECK violation, missing column), NOT a missing function
 curl -s -X POST "$URL/update_project_branding" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
 -H "Content-Type: application/json" \
 -d '{"p_project_id":"00000000-0000-0000-0000-000000000000","p_company_name":null,"p_logo_url":null,"p_theme":"glass","p_accent":null}'
 ```

 Diagnostic logic:
 - `PGRST202` → function absent or arg names/types differ from the client call → re-deploy the
 RPC (see `supabase/deploy_branding_rpc.sql` — `drop function if exists` + `create or replace`,
 because PG won't OR REPLACE a function whose signature changed).
 - `P0001` → function is fine; the failure is a runtime error inside (CHECK constraint on
 `brand_theme` missing a new theme value is the classic one). Fix = extend the CHECK
 (DROP CONSTRAINT IF EXISTS + ADD + `NOTIFY pgrst, 'reload schema';`), hand to founder as
 bare SQL.
 - **"Two 400 lines for one click" is normal here** — a blur handler (company name) and the
 theme click both call saveBranding, each carrying the full state incl. `p_theme='glass'`;
 both fail on the same CHECK. It's one root cause, not two bugs.
 - **Vault/notes claiming a migration "was applied" can be aspirational** — always verify the
 live constraint/function with a probe (or a SELECT the founder runs) before trusting that
 the DB matches the repo.

## Founder output preference (SQL hand-off)

When handing SQL for the user to paste into the Supabase SQL Editor, give a **bare,
comment-free, copy-paste-safe code block** — no `-- notes`, no explanatory prose inline.
The founder explicitly asked "write me a clean code not with ur comment etc" and "write
me the corrected sql in complete form to copy paste." Annotate in chat if needed, but the
pastable block must be clean. This overrides the usual "explain the migration" habit for
THIS founder. (DB rationale/why can still go in the prose around the block.)

## R-Tessera ↔ LunaV geo-linking (cross-project, same backend)

LunaV (Next) and R-Tessera (Vite+Cesium) are SEPARATE deployments that share ONE Supabase
backend (`okzmblyboudjffaifixa`, LunaV's project). Link, don't merge. (Note: this differs
from the Supabase account landscape table above — LunaV and R-Tessera here intentionally
share LunaV's backend; the table describes the OTHER inventedmaru projects.)

- **Canonical spec:** `~/Documents/obsidian_maru_1/Projects/R-Tessera-LunaV-Linking.md` is
  the living architecture doc — it carries phasing status, HEAD commit refs, and an
  OPEN ITEMS list. When the founder says "close them" (open items), VERIFY each against the
  actual code first — items listed at a checkpoint are often already shipped by later
  commits (e.g. Glass backdrop-blur was listed open but the shipped theme already has
  blur values). Implement the genuinely-open ones, then update the doc's HEAD refs +
  OPEN ITEMS section in the same pass. Striking a dormant/theoretical item is fine;
  note the condition that would re-open it.

- **Flow:** LunaV dashboard → "Link to R-Tessera" mints `handoff_token` via
  `mint_handoff_token` RPC, opens R-Tessera `?link=1&project=<id>&token=<h>&name=<n>&share=<s>`
  in a popup (open the window SYNCHRONOUSLY before the await — see Popup-blocker pitfall).
- **R-Tessera saves the pin:** `upsert_project_node` (SECURITY DEFINER) verifies
  `p_handoff_token = projects.handoff_token`, then INSERT/UPDATE one row per
  `lunav_project_id`. No `hmac`/`pgcrypto` (not enabled) — use `gen_random_uuid()`.
- **R-Tessera reads the node index:** anon `select` from `project_nodes` (public index).
  The Projects layer must default ON (`showProjects` initial state = `true`) or the
  pinned node "vanishes on refresh" because the layer is simply hidden, not absent.
- **R-Tessera → LunaV back-link:** node info card [View Homepage] →
  `/project/<id>/home`; [Go to Project] → public `/share/<token>` or private `/login?project=<id>`.

### CRITICAL — anon "View Homepage" 404 (learned 2026-08-10)
The LunaV homepage server component (`src/app/project/[id]/home/page.tsx`) calls
`notFound()` when anon AND no `?share=<token>`:
```ts
if (!canEdit && !siteBundle?.project) notFound();   // siteBundle only set if ?share= present
```
So a "public" node clicked by anon 404s UNLESS the URL carries `?share=<token>`.
R‑Tessera's [View Homepage] button historically sent bare `/project/<id>/home`
(no token) → 404 "project homepage is missing". **Fix (applied in R‑Tessera
`ProjectNodes.jsx`):** mirror the `goToUrl` public logic — append the node's
`lunav_share_token` when `visibility === 'public'`:
```js
const homepageUrl = (n) =>
  n.visibility === 'public' && n.lunav_share_token
    ? `${LUNO_URL}/project/${n.lunav_project_id}/home?share=${n.lunav_share_token}`
    : `${LUNO_URL}/project/${n.lunav_project_id}/home`;
```
This reuses the existing `get_shared_project` read path (no LunaV schema change).
The [Go to Project] button was already correct (`/share/<token>`).
PITFALLS:
- If anon homepage STILL 404s after this fix, the node's `lunav_share_token` is
  empty in `project_nodes` (or the project has no `handoff_token`) — check the
  node row, not the routing.
- `src/middleware.ts` must allow `/project/<id>/home` via
  `path.startsWith("/project/") && path.endsWith("/home")` — otherwise it 307→/login
  instead of 404, masking the real issue.
- **Anon key is hardcoded in R-Tessera** `src/lib/supabaseClient.js` (public by design,
  bypasses Vercel env vars). When Supabase rotates the JWT secret, this hardcoded key AND
  LunaV `.env.local` go stale together → "Invalid API key" everywhere. Refresh from the
  dashboard and update BOTH. Decode the JWT to confirm `ref`/`role` before assuming a
  schema bug. A node that EXISTS in the DB but won't DISPLAY = stale-key READ failure,
  not a broken write (P43c in supabase-backend).

## Cesium in Next.js (bird's-eye Project Homepage) — DO NOT BUNDLE (historical)

The Project Homepage used to render a Cesium globe. **Do NOT** `import { Viewer } from
"cesium"` — Cesium's npm build embeds wasm as a base64 string with `\\0` inside a
template literal, which is illegal in strict-mode ES and survives Next's minifier → the
emitted chunk throws `SyntaxError: The only valid numeric escape in strict mode is '\\0'`
at runtime (the browser page appears dead / "click does nothing"; `next build` still
passes). `transpilePackages:["cesium"]` does NOT fix it. The homepage now uses Leaflet
(see above). If you ever need a Cesium globe in Next, load it from CDN at runtime (inject
`<script>`+`<link>`, use `window.Cesium`). Full technique + `node --check` verification
recipe in `references/cesium-nextjs-cdn-load.md`.

## Middleware `isPublic` gate — new routes get silently 307-redirected (CRITICAL)
`src/middleware.ts` gates every route behind an `isPublic` allow-list. ANY new
route not in that list returns **HTTP 307 → /login** — symptom looks like "I
clicked the project / button and nothing happened." When you add a public or
geo-link route (e.g. `/project/[id]/home`), ADD it to `isPublic` explicitly:
`path.startsWith("/project/") && path.endsWith("/home")`. The route itself
enforces real access (owner via session, viewers via `?share=` token → `notFound()`
for invalid). Verify with the dev server: `curl -s -o /dev/null -w "%{http_code}"
`http://localhost:3000/<route>` → expect `404` (notFound), NOT `307` (blocked).
NEVER trust "build passed" for this — the build won't catch a middleware redirect.

### The `isPublic` list also decides what is readable BEFORE consent
A route missing from `isPublic` is invisible to logged-out users — which is
correct for app screens and WRONG for anything a visitor must read first. The
legal pages (`/privacy`, `/terms`, `/cookies`) are linked from the public
landing page and open in a new tab — they MUST be in `isPublic` or a prospective
customer clicking "Privacy Policy" is bounced to `/login`. Under PDPA/GDPR a
privacy notice must be readable BEFORE registration, so this is a compliance
bug, not a cosmetic one. FIXED in V0.33 (all three paths listed) — keep them
there if `isPublic` is ever refactored, and re-run the audit loop below.

**Same class, same front door — the signup duplicate-account trap.**
`supabase.auth.signUp` returns a DECOY user with NO error when the email already
exists (anti-enumeration), so `if (error) throw` alone tells a returning user
"awaiting approval" forever while nothing is pending. `src/app/login/page.tsx`
now checks `data.user?.identities?.length === 0` and shows "already exists —
sign in or reset" (shipped V0.33). Do not remove that branch when editing login.
**Rule:** when you add a page that must be reachable without auth — legal
notices, public docs, marketing — add it to `isPublic` explicitly and verify with
the probe above. Audit the whole surface at once, don't spot-fix:
```bash
for p in / /login /privacy /terms /cookies /dashboard /admin; do
  printf '%s -> %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE$p")"
done
```
Any page you EXPECT to be public that answers `307` is this bug.

### PITFALL — a `route.ts` and a `page.tsx` CANNOT share the same segment (2026-08-25)
In the App Router, `app/wedge/route.ts` (API handler) and `app/wedge/page.tsx`
(UI) at the SAME path segment conflict: Next.js throws
`Conflicting route and page at /wedge`. Symptom during the GAP 2 wedge demo:
every `POST/GET` to `/wedge` returned **HTTP 500** with that message.
**Fix:** put the API under `app/api/<name>/route.ts` (e.g. `app/api/wedge`)
and keep the UI at `app/<name>/page.tsx`. Then BOTH `/<name>` (page) and
`/api/<name>` (endpoint) must be added to `isPublic` if they should be
session-free. Full recipe: `references/nextjs-app-router-features.md`.

### Machine-client (no-session) public endpoints — the Rover-Kit / Jetson pattern
When an edge device (Jetson / "Luna EDGE") must POST without a user session,
make the route public in `isPublic` via `path.startsWith("/api/<name>")`, and
use an in-memory store on `globalThis` (survives HMR in dev, shared across
route files). Type it once in a `global.d.ts` so both `route.ts` and `ack/route.ts`
import the SAME declaration — do NOT redeclare `globalThis.__x` per file, TS
sees the narrow type first and widens the other to `never[]`.
```ts
// src/lib/wedge-global.d.ts
export {};
declare global {
  globalThis: { __wedgeStore?: { detections: WedgeDetection[] } };
  type WedgeDetection = { id: string; camera_id: string; ts: number; class: string; confidence: number; bbox: {x:number;y:number;w:number;h:number}; acknowledged?: boolean; action?: string };
}
```
```ts
// src/app/api/wedge/route.ts — shared store init
import type { WedgeDetection } from "@/lib/wedge-global";
const store: { detections: WedgeDetection[] } =
  globalThis.__wedgeStore ?? (globalThis.__wedgeStore = { detections: [] as WedgeDetection[] });
```
In-memory resets on server restart — fine for a demo; for prod, persist to
Supabase and add an edge auth token on the endpoint.

## Middleware `matcher` regex — static `.html` is ALSO gated (2026-08-10, CRITICAL)
The `config.matcher` negative-lookahead excludes `_next/static`, `_next/image`,
`favicon.ico`, and binary extensions (`svg|png|jpg|jpeg|gif|webp|glb|obj`) — but
NOT `.html`. **Consequence:** any static HTML in `public/` (e.g. the LunaV Studio
builder `public/studio/lunav_studio_safe.html`, rendered in a workspace `<iframe>`)
is run through the auth middleware and **307-redirected to `/login`** — the iframe
loads `/login` instead of the HTML, so the "LunaV Studio" tab button looks dead
("button not working"). This is a SEPARATE mechanism from the `isPublic` route
allow-list above: it's the matcher regex, not the route list.

**Fix (committed `96e5efa`):** add `html?` + an explicit `^/studio/` exclusion:
```ts
matcher: ["/((?!_next/static|_next/image|favicon.ico|studio/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|glb|obj|html?)$).*)"],
```
**Verification recipe (against the running dev server):**
```bash
# BEFORE fix: 307 -> /login (BROKEN)
curl -sI http://localhost:3000/studio/lunav_studio_safe.html | grep -iE "HTTP/|location"
# AFTER fix: 200, body is the studio HTML (58KB, contains 'LunaV Studio' + 'canvas-container')
curl -s http://localhost:3000/studio/lunav_studio_safe.html | grep -c "LunaV Studio"
```
- Rule: if you add ANY new static page under `public/` (`.html`, or a new iframe
  target), add its extension/dir to the matcher exclusion — otherwise the same
  307-on-iframe bug returns.
- The LunaV Studio builder (`public/studio/lunav_studio_safe.html`) loads Three.js
  from `https://unpkg.com` via an ES-module importmap. On Vercel that depends on
  outbound egress to unpkg; to harden (offline + CSP-safe) vendor Three.js into
  `public/studio/vendor/` and rewrite the importmap to local paths.
- **Deprecation:** Next.js now warns the `middleware.ts` convention is deprecated
  in favor of `proxy.ts`. Functional, but rename to clear the warning.
- Full repro + matcher diff: `references/lunav-studio-iframe.md`.

## What the "LunaV STUDIO" tab actually IS (and is not)

The workspace Studio tab is a plain `<iframe src="/studio/lunav_studio_safe.html">`
(`public/studio/lunav_studio_safe.html`, ~58KB of self-contained HTML). Know its real
shape before answering questions about it:

- It is **client-side only**. Three.js loads from unpkg via an ES-module importmap;
the geometry is built in the browser with `BoxGeometry` / `CylinderGeometry` /
`ExtrudeGeometry` / `LatheGeometry` and exported through `GLTFExporter`.
- **BYOK = the user's own Gemini API key.** The page takes a key in a password input and
calls `generativelanguage.googleapis.com` DIRECTLY from the browser (`?key=<apiKey>`)
to list models and to `generateContent`. There is no server route, no proxy, no
Supabase function in this path. The key never leaves the browser tab.
- **It does NOT use Blender, and it is NOT the headless-Blender pipeline.** That is a
separate thing living in the LUNASCAN repo (`lunascan/object/` — `codegen.py` emits a
build script, `build.py` runs `blender --background --python-exit-code 1 --python …`,
with `discover_blender()` probing `/usr/local/bin`, `/opt/homebrew/bin`, `/usr/bin`).
Two different 3D-producing systems; do not conflate them when asked. Same file also
exists under `ARRAS/public/studio/`.

## PITFALL — verify a deliverable by CONTENT, not by filename or mtime alone
A file handed over as a model/splat deliverable can be silently overwritten by whatever
app the user opened it in. Observed: a 3DGS `.ply` (29MB, 62 properties, binary) became a
5.5MB ASCII mesh `.ply` with `comment object: <name>1` — the signature of an editor's
export — and the original was gone at that path.

Before reporting a deliverable as good, read its header and assert the format you wrote:
`ply` + `format binary_little_endian 1.0` + the expected property count (62 for SH degree
3) + no duplicate property names. A filename and a plausible size prove nothing.
When you catch this, re-pull from the source of truth and write it under a DIFFERENT
filename (append the format, e.g. `_3dgs.ply`) so the overwrite cannot recur.

## Scoping a new feature into this workspace: check the surface before designing

Founder asks about a new panel/tab arrive with an assumed structure. Verify the real one
first, because this app's chrome is not what the naming suggests:

- **There is no Settings PAGE.** Settings is a dropdown on the workspace header
  (`settingsOpen`), whose items today are: Export Link · AR Sheet · Appearance · LunaV LABS
  (external) · LunaV STUDIO (sets the tab) · LunaV R-TESSERA (external) · Privacy · Terms.
  New top-level destinations belong here as dropdown entries, NOT as new nav tabs.
- **Tabs are `tab === "3d" | "studio" | "certificates" | "report" | "analytics" | "docs"`**,
  rendered as `hidden`-toggled absolutely-positioned divs, not routes.
- **`ImportScanModal.tsx` is ORPHANED** — it imports LUNASCAN `.glb`s from R2 but nothing
  renders it (the button was removed). `models.source` still carries the `'lunascan'`
  value. Do not describe it as a live feature.
- **A GPU job/queue/worker concept NOW EXISTS (added V0.27/V0.28).** The repo carries
  `gpu_jobs` + `gpu_workers` tables, a `profiles.gpu_access` per-account gate, and
  service_role-only RPCs (`claim_gpu_job` / `heartbeat_gpu_worker` / `finish_gpu_job`)
  plus `can_use_gpu()` / `cancel_gpu_job` / `set_gpu_access`. A worker on a separate
  NAT'd GPU box polls the queue and runs `odm` / `splat` / `yolo` jobs. UI: the
  Settings → LunaV STUDIO tab has FOUR sub-tabs (`LUNASCAN` job panel |
  `Model Library` | `AI Training` | `AI Model Generator` = the pre-existing
  safe-JSON/BYOK builder, MOVED not deleted), plus a new Settings → **LunaV EDGE** entry, plus a header GPU
  status chip (`GpuStatusChip.tsx`, green=idle / blue=running / amber=unreachable)
  beside Settings. Job data helpers live in `src/lib/gpuJobs.ts`; model-library helpers
  in `src/lib/modelLibrary.ts`; panels in `src/components/LunascanPanel.tsx`,
  `LunavEdgePanel.tsx`, `ModelLibraryPanel.tsx`.
- **Model Library lists BOTH storage homes.** `models` rows point at either an R2
  `pub-*.r2.dev` URL (browser uploads) or a Supabase Storage public URL (published
  GPU results); classify by host to show provenance. A GPU result only becomes
  viewable after a **Publish** action on a DONE job: it copies the private result
  from the `gpu-jobs` bucket into the PUBLIC `models` bucket and inserts a
  `public.models` row, so the viewer's existing read path picks it up. Until then the
  job is DONE but has no viewable artifact — "job done" and "model on the globe" are
  two different states, and the UI should not conflate them.
- **There is still no connection-status component for anything OTHER than the GPU
  worker.** If the founder refers to an existing "PC2 status indicator", the one that
  exists is the GPU chip above; anything else needs designing fresh. Do not invent a match.
- **Job-file storage defaults to Supabase Storage, not R2.** Bucket `gpu-jobs`
  (private) for job results; bucket `models` (public) for anything the viewer must
  load. The worker's backend is switchable via `STORAGE_BACKEND`. Supabase Storage
  object paths are BUCKET-RELATIVE — a key that already starts with the bucket name
  double-prefixes to `<bucket>/<bucket>/...` and the object becomes unreachable while
  the job still reports DONE. Fetch and verify the artifact rather than trusting the
  row status.
- **The `models` table's `file_url` must be PUBLICLY readable** for the 3D viewer to
  load it without auth. `public.models` RLS scopes rows to the project owner, but the
  FILE is fetched by URL, so the storage bucket has to be public (or the URL signed).
  Publishing therefore means: private staging bucket → public delivery bucket → row.
- **A new column is not live until the founder pastes the SQL.** Column adds need DDL,
  which the REST API cannot do (no `exec_sql`), and the Management API rejects the
  service_role key. So schema changes always end as a bare comment-free paste file
  (see the SQL hand-off rule). A code-only Vercel deploy never touches the schema — the
  UI then reads a missing column and shows empty state, not an error.

### Naming caution when splitting an existing tab into sub-tabs
"LunaV Studio" is BOTH the product name of the whole app AND the name of this one tab.
When asked to add a second sub-tab and park existing content under its own tab, restate
the mapping in the reply (which label sits where) before building, so an ambiguous rename
is caught before the edit rather than after.

## AI Training tab (Settings → LunaV STUDIO → AI Training)
Label objects in frames and export a YOLO dataset; training itself runs on the
NAT'd GPU box (see `remote-gpu-job-queue`). Files:
- `src/components/LabelCanvas.tsx` — self-contained labelling canvas: box draw,
  zoom/pan, class picker, `autoSuggest` hook, keyboard shortcuts (1-9 class,
  Delete, Cmd/Ctrl+S, arrows). **It takes frames via props and emits via
  callbacks — it must never touch storage**, so the SAME component serves both
  the webapp and the Mac Luna-EDGE app.
- `src/components/LabelPanel.tsx` — dataset CRUD, client-side video frame
  extraction (2 fps, cap ~200), image upload, class management, YOLO zip export
  via `jszip`, gated on `fetchGpuAccess()` like LUNASCAN.
- Schema: `label_datasets` / `label_frames` / `label_boxes`, RLS scoped through
  `projects.owner_id = auth.uid()`, private bucket `label-frames`. The storage
  policy keys on `split_part(name,'/',1) = dataset_id`, so **frame storage keys
  MUST be `<dataset_id>/frames/<file>.jpg`** — a key without the dataset id as
  the first path segment is unreadable.

Pitfalls that cost time here:
- **Async upload callbacks capture stale React state.** The frame-extraction and
  image-upload loops read `frames` from the closure and compute a wrong
  `frame_count`. Keep a `framesRef.current` and read the ref for any count math
  inside an async loop.
- **YOLO labels are centre-normalised, not corner-normalised.** The canvas stores
  `{x,y,w,h}` top-left origin; the export MUST convert:
  `cx = x + w/2`, `cy = y + h/2` (all already 0-1 normalised). Writing x/y/w/h
  straight out produces a model that trains on garbage.
- **Export needs `jszip`** (not previously a dependency) — add it before wiring
  the export path.

NOT built: the `train` job kind on the GPU queue. Export downloads a zip to the
user; nothing yet uploads a dataset and returns a `.pt`. Do not describe training
as working — say the export works and training is the next piece.

## Dashboard error feedback (V0.34) — do not re-report it as missing
`src/app/dashboard/page.tsx` now carries a toast system plus a `friendlyError()`
translator (row-level-security / duplicate-key / network / expired-session →
plain language) wired to every mutation AND the initial load. Errors persist 7s
(info 3.5s) and the queue caps at 5, so an error is never evicted by a burst.
`createProject` now guards the session instead of a `userData.user!.id` non-null
assertion that threw a raw TypeError on an expired session.
- **Verifying a fix on an AUTH-GATED route:** `/dashboard` 307s a logged-out
  `curl` to `/login`, so the page HTML proves nothing. Grep the built chunk
  instead — `grep -rl "<new string>" .next/static/chunks/` locally, then fetch
  that exact chunk from the live origin and confirm HTTP 200 + the string.
  Chunk names are content-hashed, so a 404 means your local `.next` is from a
  different build than production.

## Same-route `router.push` is dead for tab switches (2026-08-10)
A Settings-dropdown item that does `router.push(\`/project/${id}?tab=studio\`)` while
the user is ALREADY on `/project/[id]` does NOT switch tabs: Next.js same-route
navigation does not remount the workspace, and `useState(effectiveInitialTab)` runs
once on mount — so the `tab` state stays put and the button appears dead. Fix:
call `setTab("studio")` directly (the workspace is already mounted); that matches
how every other tab button works. Keep `router.push` only for cross-route jumps
(e.g. homepage → workspace).

## Diagnosing "HTTP 400 on update_project_branding" (2026-08-10)
Do NOT assume "function missing" (the previous session did, and the fix didn't
stick). Probe the LIVE function first with the anon key (R-Tessera hardcodes it in
`src/lib/supabaseClient.js` for the shared backend):
- `POST /rest/v1/rpc/update_project_branding` with the exact 5 params + a bogus
  uuid → `P0001 Not project owner` means the function EXISTS and ran its body
  (the ownership check is first, so anon always hits it). `PGRST202` would mean
  actually missing.
- If the function is fine, the 400 is the UPDATE failing — almost always the
  `projects_brand_theme_check` CHECK constraint missing a newer theme value
  (`'glass'`). The app default theme is glass, so EVERY save carries glass → 400
  on every click (two 400 lines = theme click + company-name blur both firing).
- Fix: idempotent `DROP CONSTRAINT IF EXISTS projects_brand_theme_check; ADD
  CONSTRAINT ... IN ('dark','light','midnight','glass'); NOTIFY pgrst, 'reload
  schema';` — hand to founder for the SQL Editor (per DDL-delivery rule), never
  claim applied until they confirm.

## Popup-blocker: `window.open` after `await` is silently dead
A `window.open(url,"_blank")` placed AFTER `await supabase.rpc(...)` (or any async
await) is treated as a non-gesture popup and is blocked → "button did nothing /
no tab opened." Fix: open the window SYNCHRONOUSLY on the click gesture first,
then navigate it after the await:
```ts
const popup = window.open("", "_blank");
try {
  const { data, error } = await supabase.rpc("mint_handoff_token", { p_project_id: p.id });
  if (error) throw error;
  const url = `https://r-tessera.vercel.app/?link=1&project=${p.id}&token=${data}`;
  if (popup) popup.location.href = url; else window.open(url, "_blank");
} catch (e) { if (popup) popup.close(); alert(`... ${e.message}`); }
```
Applies to ANY "open external link after fetching a token/URL" button.

## Deployment & verification

### Fresh database setup (first deploy or new Supabase)

The DB schema lives in `supabase/schema.sql`. This file creates ALL tables (`profiles`, `projects`, `models`, `markers`, `documents`, `proxies`) plus RLS policies and share-token functions. Everything uses `create if not exists` — safe to re-run.

**Run order is critical:**

1. **`supabase/schema.sql` FIRST** — creates the tables. The `models` table (with `source` column) is created here.
2. **Individual migrations** (e.g. `20260805_lunascan_import.sql`) are ONLY for adding incremental changes to an EXISTING schema. They will fail if the table doesn't exist.

Do NOT run migration files before schema.sql. The migration `20260805_lunascan_import.sql` only adds a `source` column to an existing `models` table — it's redundant if you already ran the latest `schema.sql`, but harmless (idempotent).

**How to run:** Open https://supabase.com/dashboard/project/okzmblyboudjffaifixa → SQL Editor → paste full file → Run.

### Edge function deploy

Two options:

**Via dashboard (recommended when CLI is on wrong account):**
1. https://supabase.com/dashboard/project/okzmblyboudjffaifixa → Edge Functions
2. Click green "Deploy a new function" → "Via Editor"
3. Name: `r2-list`, paste content of `supabase/functions/r2-list/index.ts` → Deploy

**Via CLI (when logged in as kingkymaru):**
```bash
cd ~/Documents/ss-rover-cloud
supabase login    # must be kingkymaru account
supabase link --project-ref okzmblyboudjffaifixa
supabase functions deploy r2-list
```
The CLI may be logged into the wrong account (`inventedmaru@gmail.com`). Run `supabase projects list` to see which account you're targeting — if you see AnglerGO/r-tessera, you're on the wrong account.

### Build verification

```bash
cd ~/Documents/ss-rover-cloud
npx tsc --noEmit && npm run build
```

If build fails on `/admin` prerendering: NEXT_PUBLIC_* env vars are missing. Create `.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://okzmblyboudjffaifixa.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=placeholder-for-build
```
`.env*` is already in `.gitignore` — the file won't be committed. Real values are set in Vercel dashboard.

### Running the real app locally against REAL data

A placeholder anon key only satisfies the build. To actually load a project, two things bite:

1. **The key is a placeholder and the Vercel CLI cannot hand it over.** `vercel env pull`
   writes `[SENSITIVE]` in place of both Supabase secrets. The anon key IS public by design —
   it ships in the browser bundle — so scrape it from the deployed app instead: crawl
   `/dashboard`, `/login` and their `_next/static` chunks, regex a JWT (`eyJ...`), then decode
   the payload and assert `role: "anon"` and `ref: "okzmblyboudjffaifixa"` before using it.
   The homepage HTML alone does not carry it; the chunk for an authed route does. Write it into
   `.env.local` next to the URL, back up any existing file first, never commit it.
2. **Anon RLS returns zero rows.** With the anon key every table answers 200 but `projects`
   returns `content-range: */0` — projects are owner-scoped. The app therefore cannot show
   real data until a HUMAN signs in. Do not ask for or type a password: start `npm run dev`,
   hand over `http://localhost:3000`, and let the founder sign in himself.

Treat a local run against production as READ-ONLY unless told otherwise — the same server can
write to the live database, so any new design screen must be read-only by construction and you
should say plainly that the real workspace still writes.

### Rebuilding a real screen as an isolated design page (zero edits to existing code)

When the founder wants a different look for an existing screen "using the actual code and data"
but must not disturb the live app, add a ROUTE and a COMPONENT — never edit the screen.

- `src/app/<name>/page.tsx` — a server component that repeats the real page's data loading
  (project → models → markers → proxies → zones → certificates → node_documents), tolerating a
  missing table the same way the production page does (error → `[]`).
- `src/components/<Name>.tsx` — a client component that imports the REAL `Viewer3D` unchanged
  and wraps it in new chrome. Pass `readOnly` and no-op callbacks so the page physically
  cannot write.
- **Adding an optional prop to a shared component still counts as modifying it.** If the viewer
  has no lighting prop and you may not add one, apply the effect from OUTSIDE: wrap it in a div
  with `style={{ filter: "brightness(200%)" }}`. A CSS filter on a WebGL canvas
  works and costs the component nothing.
- **Prove the claim with git, not prose:** `git status --porcelain` must show only untracked
  new files. One tracked file appearing means you changed something you said you would not.
- **The app's global footer is `fixed inset-x-0 bottom-0 z-50`, ~33px tall.** A new full-bleed
  page at `inset:0` gets its own bottom strip painted over and buries the version stamp.
  Offset the new root: `position:fixed; top:0; left:0; right:0; bottom:33px`.
- **Verifying the layout without logging in:** every route outside the middleware `isPublic`
  list 307s to `/login`, and editing the middleware is off-limits. Put the throwaway preview
  under an ALREADY-public prefix — `src/app/share/tmp-preview/page.tsx` — render the new
  component with empty props, confirm it renders, then delete the route. A static segment
  beside `share/[token]` wins for that exact path.

- Do NOT confuse LunaV with R-Tessera (`~/my-digital-twin`). They are completely independent projects with different stacks (Three.js vs Cesium) and different architectures. The user treats them as separate and does not want cross-project comparisons.
- **LunaV's Supabase is `okzmblyboudjffaifixa` under kingkymaru** — NOT the AnglerGO project (`merfmrlkjoqrhijzfwbn` under inventedmaru@gmail.com). These are different accounts with different projects. The `supabase` CLI may default to whichever account you last logged into — always check `supabase projects list` or the skill's project ref before targeting a database.
- **`npm run build` fails on `/admin` prerender** when `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY` are missing from the local env. Even `"use client"` pages are SSR-prerendered by Next.js, which calls `createBrowserClient` at build time. Fix: create `.env.local` with placeholder values (auto-gitignored by `.gitignore`'s `.env*` rule). Real values live in Vercel dashboard.
- The model auto-scaling (`25 / Math.max(size.x, size.y, size.z)`) means markers are only valid for the exact model they were placed on. Swapping models requires a bounding-box-aware position correction.
- `gltf-pack.ts` is used to convert split glTF uploads to single GLB before R2 upload, since the viewer only handles single-file formats.
- Markers are scene siblings, not model children — they don't move with the model. This is by design since the model is static.
- **RPC `RETURNS TABLE` column-order bug (Error 42P13):** In `CREATE FUNCTION ... RETURNS TABLE(...)`, Postgres matches CTE columns to return columns by **position, not name**. If you get `ERROR: 42P13: return type mismatch ... returns uuid instead of timestamp with time zone at column 4`, check that the CTE SELECT column order exactly matches the RETURNS TABLE declaration order.